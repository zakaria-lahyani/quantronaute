from typing import Optional, Dict, Any, List

from app.strategy_builder.data.dtos import EntryDecision
from app.trader.risk_manager.models import ScalingConfig, PositionGroup, ScaledPosition, PositionType
from app.trader.risk_manager.stop_loss_calculator import MonetaryStopLossCalculator, PositionEntry
import logging
import uuid


class RiskCalculator:
    """
    1. Takes entry decision and splits into multiple limit orders
    2. Sends all orders at once
    3. Manages position groups for stop loss coordination
    4. Updates positions each iteration
    """
    def __init__(
            self,
            scaling_config: ScalingConfig,
            group_stop_loss: bool = True,
            logger: Optional[logging.Logger] = None
    ):
        self.scaling_config = scaling_config
        self.group_stop_loss = group_stop_loss  # True = single group SL, False = individual SLs
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Track position groups
        self.position_groups: Dict[str, PositionGroup] = {}
        self.active_tickets: Dict[str, str] = {}  # ticket_id -> group_id

    def _create_position_group(self, entry_decision: EntryDecision, group_id: str) -> PositionGroup:
        """Create position group from entry decision."""
        return PositionGroup(
            group_id=group_id,
            symbol=entry_decision.symbol,
            strategy_name=entry_decision.strategy_name,
            direction=entry_decision.direction,
            original_decision=entry_decision,
            total_target_size=entry_decision.position_size,
            num_entries=self.scaling_config.num_entries,
            scaling_strategy=self.scaling_config.scaling_type,
            total_risk_amount=self.scaling_config.max_risk_per_group
        )

    def _calculate_scaled_entry_prices(self, current_price: float, direction: str) -> List[
        float]:
        """Calculate entry prices for scaled positions."""
        entry_prices = []
        is_long = direction.lower() == 'long'

        # Use current price as base for spacing
        base_price = current_price
        spacing_amount = base_price * (self.scaling_config.entry_spacing / 100.0)

        for i in range(self.scaling_config.num_entries):
            if is_long:
                # For long: spread entries below current price (buy the dip)
                entry_price = base_price - (spacing_amount * i)
            else:
                # For short: spread entries above current price (sell the rally)
                entry_price = base_price + (spacing_amount * i)

            entry_prices.append(entry_price)

        return entry_prices

    def process_entry_signal(self, entry_decision: EntryDecision, current_price: float) -> Dict[str, Any]:
        """
        Process entry decision and create scaled limit orders.

        Args:
            entry_decision: Original entry decision from entry manager
            current_price: Current market price

        Returns:
            Dictionary with all limit orders to send to broker
        """
        # Create position group
        group_id = str(uuid.uuid4())
        group = self._create_position_group(entry_decision, group_id)

        # Calculate scaled entry prices
        entry_prices = self._calculate_scaled_entry_prices(
            current_price,
            entry_decision.direction
        )

        # Calculate scaled position sizes
        size_ratios = self.scaling_config.get_size_ratios()

        # Get the calculated stop loss level from the original decision (already calculated by risk manager)
        original_stop_level = entry_decision.stop_loss.level if entry_decision.stop_loss else None

        # Calculate stop losses based on mode
        if self.group_stop_loss:
            # Use the stop loss calculator to maintain constant dollar risk
            calculator = MonetaryStopLossCalculator(entry_decision.symbol, self.logger)
            
            # Create position entries for calculation
            position_entries = [
                PositionEntry(
                    entry_price=entry_prices[i],
                    position_size=entry_decision.position_size * size_ratios[i]
                )
                for i in range(len(entry_prices))
            ]
            
            # Determine which method to use for stop loss calculation
            if original_stop_level:
                # We have a stop loss level from the entry decision
                if entry_decision.stop_loss.type == 'monetary':
                    # Type is monetary but we still have a level - use the monetary risk amount
                    # The level was likely calculated elsewhere based on monetary risk
                    # So we use the configured max_risk_per_group
                    group_sl_level, sl_details = calculator.calculate_group_stop_loss(
                        position_entries,
                        self.scaling_config.max_risk_per_group,
                        entry_decision.direction
                    )
                    self.logger.info(f"Using monetary risk method: ${self.scaling_config.max_risk_per_group}")
                else:
                    # Type is 'fixed', 'atr', or other price-based stop loss
                    # Calculate risk from the original price levels
                    group_sl_level, sl_details = calculator.calculate_group_stop_loss_from_price_level(
                        entries=position_entries,
                        original_entry_price=entry_decision.entry_price,
                        original_stop_price=original_stop_level,
                        original_position_size=entry_decision.position_size,
                        direction=entry_decision.direction
                    )
                    self.logger.info(f"Using price level method: Entry {entry_decision.entry_price}, Stop {original_stop_level}")
            else:
                # No stop loss level provided, use monetary risk directly
                group_sl_level, sl_details = calculator.calculate_group_stop_loss(
                    position_entries,
                    self.scaling_config.max_risk_per_group,
                    entry_decision.direction
                )
                self.logger.info(f"No stop level provided, using monetary risk: ${self.scaling_config.max_risk_per_group}")
            
            adjusted_stops = [None] * len(entry_prices)  # No individual SLs
            
            # Log the calculation details
            self.logger.info(f"Stop loss calculation details: {sl_details}")
        else:
            # Individual stop losses - same level for all positions (simple approach)
            adjusted_stops = [original_stop_level] * len(entry_prices)
            group_sl_level = None

        # Create limit orders
        limit_orders = []

        for i in range(self.scaling_config.num_entries):
            position_id = f"{group_id}_pos_{i + 1}"
            entry_price = entry_prices[i]
            position_size = entry_decision.position_size * size_ratios[i]
            stop_loss = adjusted_stops[i]

            # Create scaled position
            position = ScaledPosition(
                position_id=position_id,
                group_id=group_id,
                symbol=entry_decision.symbol,
                direction=entry_decision.direction,
                entry_price=entry_price,
                position_size=position_size,
                stop_loss_level=stop_loss,
                position_type=PositionType.INITIAL if i == 0 else PositionType.SCALE_IN,
                strategy_name=entry_decision.strategy_name,
                magic_number=entry_decision.magic
            )

            # Add take profit targets (same for all positions)
            if entry_decision.take_profit and entry_decision.take_profit.targets:
                position.take_profit_targets = [
                    {
                        'level': target.level,
                        'percent': target.percent,
                        'value': target.value,
                        'move_stop': target.move_stop
                    }
                    for target in entry_decision.take_profit.targets
                ]

            group.add_position(position)

            # Create limit order
            limit_order = {
                'ticket_id': position_id,
                'symbol': entry_decision.symbol,
                'order_type': 'BUY_LIMIT' if entry_decision.direction.lower() == 'long' else 'SELL_LIMIT',
                'volume': position_size,
                'price': entry_price,
                'stop_loss': stop_loss if not self.group_stop_loss else None,  # Individual SL only if not group mode
                'take_profit': entry_decision.take_profit.targets[
                    0].level if entry_decision.take_profit and entry_decision.take_profit.targets else None,
                'magic': entry_decision.magic,
                'comment': f"Scale_{i + 1}/{self.scaling_config.num_entries}_{entry_decision.strategy_name}",
                'group_stop_loss': group_sl_level if self.group_stop_loss else None
            }

            limit_orders.append(limit_order)

            # Track ticket to group mapping
            self.active_tickets[position_id] = group_id

        # Store group stop loss level
        if self.group_stop_loss:
            group.group_stop_loss = group_sl_level

        # Store position group
        self.position_groups[group_id] = group

        # Calculate the actual risk amount if we have stop loss details
        calculated_risk = sl_details.get('calculated_total_risk', self.scaling_config.max_risk_per_group) if self.group_stop_loss and 'sl_details' in locals() else self.scaling_config.max_risk_per_group
        
        result = {
            'group_id': group_id,
            'limit_orders': limit_orders,
            'total_orders': len(limit_orders),
            'total_size': entry_decision.position_size,
            'scaled_sizes': [entry_decision.position_size * r for r in size_ratios],
            'entry_prices': entry_prices,
            'stop_losses': adjusted_stops,
            'group_stop_loss': group_sl_level if self.group_stop_loss else None,
            'stop_loss_mode': 'group' if self.group_stop_loss else 'individual',
            'original_risk': self.scaling_config.max_risk_per_group,
            'calculated_risk': calculated_risk,
            'weighted_avg_entry': sl_details.get('weighted_avg_price') if self.group_stop_loss and 'sl_details' in locals() else None,
            'stop_calculation_method': 'price_level' if original_stop_level and entry_decision.stop_loss and entry_decision.stop_loss.type != 'monetary' else 'monetary'
        }

        self.logger.info(
            f"Created {len(limit_orders)} scaled limit orders for {entry_decision.symbol} "
            f"{entry_decision.direction} (Group: {group_id[:8]})"
        )

        return result

