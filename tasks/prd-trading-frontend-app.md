# PRD: Quantronaute Trading Frontend Application

## Introduction/Overview

The Quantronaute Trading Frontend is a comprehensive web-based trading platform built with Next.js and Tailwind CSS. This application provides individual traders with a powerful, modern interface to monitor their trading positions, execute manual trades, control automation strategies, and analyze account performance in real-time.

**Problem Statement**: Traders currently lack a user-friendly interface to interact with the Quantronaute trading API. They need a centralized dashboard to monitor positions, manage risk, control automation, and execute manual trades without using command-line tools or API clients.

**Solution**: A dark-themed, dashboard-style web application that provides real-time trading data visualization, manual trading controls, automation management, and comprehensive account analytics through an intuitive, customizable interface.

## Goals

1. **Primary Goal**: Deliver a production-ready trading platform that enables traders to manage their accounts efficiently through a visual interface
2. **User Experience Goal**: Provide sub-5-second response times for all trading operations with clear feedback on action success/failure
3. **Reliability Goal**: Achieve 99.9% uptime with automatic reconnection on API disconnects
4. **Scalability Goal**: Support multiple trading accounts with seamless switching and combined portfolio view
5. **Adoption Goal**: Enable traders to perform 100% of trading operations through the UI without requiring API knowledge

## User Stories

### Authentication & Session Management
- As a trader, I want to securely log in with my credentials so that I can access my trading dashboard
- As a trader, I want the application to remember my session so I don't have to login repeatedly within a day
- As a trader, I want to log out securely so that my account remains protected

### Position Monitoring
- As a trader, I want to see all my open positions at a glance so I can quickly assess my current exposure
- As a trader, I want to see real-time P&L updates on my positions so I can make informed decisions
- As a trader, I want to view position details (entry price, current price, stop loss, take profit) so I understand my risk/reward
- As a trader, I want to filter and sort positions by symbol, P&L, or time opened so I can focus on specific trades

### Manual Trading
- As a trader, I want to manually open a new position with customizable parameters (symbol, direction, risk, SL/TP) so I can execute my trading ideas
- As a trader, I want to manually close existing positions (full or partial) so I can take profits or cut losses
- As a trader, I want to modify stop loss and take profit levels on open positions so I can adjust my risk management
- As a trader, I want clear confirmation before executing trades so I don't make accidental mistakes

### Automation Control
- As a trader, I want to toggle automation on/off with a single click so I can quickly control automated trading
- As a trader, I want to see the current automation status clearly displayed so I always know if strategies are active
- As a trader, I want to see which strategies are enabled/disabled so I can control individual strategy behavior

### Account Analytics
- As a trader, I want to view my account balance, equity, and margin usage so I understand my account health
- As a trader, I want to see daily/weekly/monthly P&L charts so I can track my performance over time
- As a trader, I want to view win rate, average win/loss, and other performance metrics so I can analyze my trading effectiveness
- As a trader, I want to export performance data so I can conduct deeper analysis

### Risk Management
- As a trader, I want to see my current risk exposure as a percentage of account so I stay within my limits
- As a trader, I want to see daily drawdown metrics so I can monitor if I'm approaching risk limits
- As a trader, I want visual warnings when risk thresholds are approached so I can take action

### Multi-Account Support
- As a trader, I want to switch between multiple trading accounts so I can manage different strategies/portfolios
- As a trader, I want to see a combined view of all accounts so I can understand my total portfolio exposure
- As a trader, I want account-specific settings to persist when switching accounts

### System Monitoring
- As a trader, I want to see system health status so I know if the trading system is operating correctly
- As a trader, I want to see API connection status so I'm aware of any connectivity issues
- As a trader, I want to receive alerts when system issues occur so I can react promptly

## Functional Requirements

### FR1: Authentication System
1. The application must provide a login page with username and password fields
2. The application must authenticate users against the Quantronaute API (`POST /auth/login`)
3. The application must store JWT access and refresh tokens securely (httpOnly cookies or localStorage with encryption)
4. The application must automatically refresh expired access tokens using the refresh token
5. The application must redirect unauthenticated users to the login page
6. The application must provide a logout function that clears tokens and redirects to login
7. The application must display authentication errors clearly (invalid credentials, expired session, etc.)
8. The application must implement session timeout after 30 minutes of inactivity with warning dialog

### FR2: Dashboard Layout
9. The application must display a main dashboard with a sidebar navigation and top header
10. The sidebar must include navigation to: Dashboard, Positions, Manual Trading, Automation, Analytics, Risk, Settings
11. The top header must display: account selector, system status indicator, user profile menu
12. The dashboard must be responsive and usable on desktop screens (1920x1080 minimum)
13. All components must use dark mode theme by default
14. The layout must support customizable widget arrangement (drag-and-drop or preset layouts)

### FR3: Position Monitoring
15. The application must display all open positions in a table/card view
16. Each position must show: symbol, direction (long/short), entry price, current price, unrealized P&L, P&L %, stop loss, take profit, position size
17. The application must update position data every 10 seconds via API polling (`GET /positions`)
18. The application must color-code P&L values (green for profit, red for loss)
19. The application must allow filtering positions by symbol, direction, or P&L range
20. The application must allow sorting positions by any column (symbol, P&L, time opened, etc.)
21. The application must display total open positions count and combined P&L prominently
22. Clicking a position must show detailed position information in a modal/side panel

### FR4: Manual Trading Interface
23. The application must provide a "New Trade" button/form accessible from the dashboard
24. The new trade form must include fields for: symbol (dropdown or autocomplete), direction (long/short toggle), risk amount, stop loss (pips or price), take profit (pips or price)
25. The application must calculate position size automatically based on risk and stop loss
26. The application must validate all trade parameters before submission
27. The application must submit trade to API (`POST /signals/entry`) and show loading state
28. The application must display success confirmation or error message after trade submission
29. The application must provide "Close Position" action on each open position
30. The close position action must support full or partial close (percentage slider)
31. The application must submit close requests to API (`POST /signals/exit`)
32. The application must provide "Modify Position" action to update SL/TP levels
33. All trading actions must require confirmation dialog before execution

### FR5: Automation Control
34. The application must display current automation status (enabled/disabled) prominently
35. The application must provide a toggle switch to enable/disable automation
36. Toggling automation must call API (`POST /automation/enable` or `POST /automation/disable`)
37. The application must poll automation status every 15 seconds (`GET /automation/status`)
38. The application must display list of available strategies with their enabled/disabled state
39. The application must allow individual strategy enable/disable if supported by API
40. The application must show strategy performance metrics (win rate, total trades, P&L) if available

### FR6: Account Analytics Dashboard
41. The application must fetch account data from API (`GET /account`)
42. The application must display: account balance, equity, free margin, margin level, margin used
43. The application must show daily/weekly/monthly P&L in a line chart
44. The application must calculate and display: total trades, win rate, average win, average loss, profit factor, max drawdown
45. The application must provide date range selector for analytics (last 7 days, 30 days, 90 days, YTD, All time)
46. The application must allow exporting analytics data to CSV
47. Charts must be interactive (tooltip on hover, zoom/pan capabilities)

### FR7: Risk Management Dashboard
48. The application must fetch risk status from API (`GET /risk/status`)
49. The application must display current risk exposure as percentage of account equity
50. The application must show daily P&L and drawdown metrics
51. The application must display risk limits (max positions, daily loss limit, position size limits)
52. The application must show visual progress bars for risk metrics
53. The application must display warnings when risk thresholds are approached (>80% of limit)
54. The application must show critical alerts when limits are breached
55. Risk metrics must update every 10 seconds

### FR8: Multi-Account Management
56. The application must provide an account selector dropdown in the header
57. The application must fetch and display available accounts (may require API enhancement)
58. Switching accounts must reload all dashboard data for the selected account
59. The application must store last selected account in localStorage
60. The application must provide a "Combined View" option showing aggregated data across all accounts
61. Each account must have isolated state (positions, analytics, settings)

### FR9: System Monitoring
62. The application must poll system status from API (`GET /system/status`) every 30 seconds
63. The application must display system health indicator in header (green=healthy, yellow=degraded, red=down)
64. The application must show detailed system metrics in a dedicated page/modal
65. The application must display API connection status and latency
66. The application must show toast notifications for system events (connection lost, reconnected, errors)
67. The application must implement automatic retry logic for failed API requests (3 retries with exponential backoff)

### FR10: Configuration Management
68. The application must provide a Settings page accessible from navigation
69. Settings must include: API endpoint URL, polling intervals, theme preferences, notification preferences
70. The application must allow viewing current system configuration (`GET /config`)
71. The application must allow updating configuration if user has permissions (`PUT /config`)
72. Configuration changes must require confirmation
73. The application must validate configuration before submission

### FR11: Error Handling & User Feedback
74. All API errors must be caught and displayed to user with clear messages
75. Network errors must show retry button
76. The application must show loading states for all async operations (spinners, skeleton screens)
77. Success operations must show toast notifications with confirmation
78. Form validation errors must be displayed inline near the relevant field
79. The application must implement global error boundary to catch React errors

### FR12: Performance & Data Management
80. The application must implement data caching to reduce API calls
81. Cached data must have TTL (time-to-live) and refresh strategy
82. The application must batch API requests where possible
83. The application must implement pagination for large datasets (positions history, trade history)
84. The application must lazy-load routes and heavy components
85. Initial page load must be under 3 seconds on standard broadband connection

## Non-Goals (Out of Scope)

The following features are explicitly **NOT** included in this version:

1. **Mobile Native Apps**: This is a web application only; native iOS/Android apps are not included
2. **Advanced Charting**: TradingView-style candlestick charts with indicators are not included (may use simple line charts)
3. **Social/Community Features**: No chat, trade sharing, or social trading features
4. **Backtesting**: Historical strategy backtesting is not included
5. **Custom Strategy Builder**: Visual strategy creation/editing tools are not included
6. **Email/SMS Notifications**: Only in-app notifications; external notifications are not included
7. **User Administration**: No user management, role-based access control, or multi-user collaboration
8. **White Labeling**: No customization for different brands/brokers
9. **Offline Mode**: Application requires internet connection; no offline functionality
10. **Real-time WebSocket Streaming**: Using polling instead of WebSocket for this version
11. **Order Book/Level 2 Data**: Only position data, no detailed market depth
12. **News Feed Integration**: No financial news or economic calendar
13. **PDF Report Generation**: No automated report generation; only CSV export

## Design Considerations

### UI/UX Requirements

**Visual Design**:
- Dark theme with trader-friendly color palette (dark navy/black background, cyan/green accents)
- Use Tailwind CSS for styling with custom design system
- Dashboard-style layout with card-based widgets
- Modern, clean typography (Inter or similar sans-serif font)
- Consistent spacing and component sizing (8px grid system)

**Color Scheme**:
- Background: `#0f172a` (slate-900)
- Cards/Panels: `#1e293b` (slate-800)
- Borders: `#334155` (slate-700)
- Text Primary: `#f1f5f9` (slate-100)
- Text Secondary: `#94a3b8` (slate-400)
- Profit: `#10b981` (emerald-500)
- Loss: `#ef4444` (red-500)
- Warning: `#f59e0b` (amber-500)
- Info: `#3b82f6` (blue-500)

**Components**:
- Use shadcn/ui or Headless UI for base components
- Custom trading-specific components (position card, P&L display, risk gauge)
- Responsive tables with fixed headers for large datasets
- Modal dialogs for confirmations and detailed views
- Toast notifications for feedback (top-right position)

**Layout Structure**:
```
┌─────────────────────────────────────────────────┐
│  Header (Account Selector | Status | User)     │
├──────┬──────────────────────────────────────────┤
│      │                                          │
│ Side │         Main Content Area                │
│ Nav  │     (Dashboard/Positions/Trading)        │
│      │                                          │
│      │                                          │
└──────┴──────────────────────────────────────────┘
```

### Responsive Breakpoints
- Desktop: 1920x1080 (primary target)
- Laptop: 1366x768 (must be usable)
- Tablet: Not optimized (may work but not primary focus)

### Component Library
- **Framework**: Next.js 14+ with App Router
- **Styling**: Tailwind CSS 3+
- **Components**: shadcn/ui
- **Charts**: Recharts or Chart.js
- **Forms**: React Hook Form + Zod validation
- **State Management**: Zustand or React Context
- **API Client**: Axios or native fetch with interceptors
- **Icons**: Lucide React or Heroicons

## Technical Considerations

### Architecture

**Project Structure**:
```
/frontend
├── /app                    # Next.js app directory
│   ├── /dashboard         # Dashboard pages
│   ├── /positions         # Position monitoring
│   ├── /trading           # Manual trading
│   ├── /automation        # Automation control
│   ├── /analytics         # Performance analytics
│   ├── /risk              # Risk management
│   ├── /settings          # Configuration
│   └── layout.tsx         # Root layout
├── /components
│   ├── /ui                # Base UI components
│   ├── /trading           # Trading-specific components
│   ├── /charts            # Chart components
│   └── /layout            # Layout components
├── /lib
│   ├── /api               # API client and endpoints
│   ├── /hooks             # Custom React hooks
│   ├── /utils             # Utility functions
│   └── /validators        # Zod schemas
├── /store                 # State management
└── /types                 # TypeScript types
```

**API Integration**:
- Base URL configurable via environment variable (`NEXT_PUBLIC_API_URL`)
- Axios instance with request/response interceptors
- Automatic token refresh on 401 responses
- Request retry logic with exponential backoff
- TypeScript types generated from API endpoints

**State Management Strategy**:
- Global state: Authentication, account selection, user preferences
- Server state: API data (positions, account info) - use SWR or React Query for caching
- Local state: Form inputs, UI state (modals, drawers)

**Authentication Flow**:
1. User submits login form → POST /auth/login
2. Store access_token and refresh_token in httpOnly cookies (if using API routes) or encrypted localStorage
3. Attach Authorization header to all API requests
4. On 401 response → attempt token refresh → retry original request
5. On refresh failure → redirect to login

**Data Polling Strategy**:
- Positions: 10 seconds
- Account data: 15 seconds
- System status: 30 seconds
- Risk metrics: 10 seconds
- Automation status: 15 seconds
- Use `setInterval` or SWR's refreshInterval
- Stop polling when tab is inactive (Page Visibility API)

### Dependencies

**Core**:
- next ^14.0.0
- react ^18.0.0
- typescript ^5.0.0

**UI**:
- tailwindcss ^3.0.0
- @radix-ui/react-* (via shadcn/ui)
- lucide-react (icons)

**Data & Forms**:
- axios ^1.6.0
- react-hook-form ^7.0.0
- zod ^3.0.0
- swr ^2.0.0 or @tanstack/react-query ^5.0.0

**Charts**:
- recharts ^2.0.0

**Utilities**:
- date-fns (date formatting)
- clsx or tailwind-merge (className utilities)
- zustand ^4.0.0 (state management)

### Environment Variables
```
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_POLLING_INTERVAL_POSITIONS=10000
NEXT_PUBLIC_POLLING_INTERVAL_ACCOUNT=15000
NEXT_PUBLIC_POLLING_INTERVAL_SYSTEM=30000
```

### Performance Optimizations
- Code splitting by route (automatic with Next.js)
- Lazy loading for charts and heavy components
- Memoization of expensive calculations (React.memo, useMemo)
- Debouncing search/filter inputs
- Virtual scrolling for large position lists (if >100 positions)
- Image optimization with next/image
- Tree shaking unused code

### Security Considerations
- Store tokens securely (httpOnly cookies preferred, or encrypted localStorage)
- Validate all user inputs client-side and server-side
- Sanitize data before rendering to prevent XSS
- Implement CSRF protection for state-changing operations
- Use HTTPS in production
- Implement rate limiting on form submissions
- Set appropriate Content Security Policy headers

### Browser Support
- Chrome/Edge: Last 2 versions
- Firefox: Last 2 versions
- Safari: Last 2 versions
- No IE11 support required

## Success Metrics

### User Adoption Metrics
- **Target**: 100% of target users complete at least one manual trade via UI within first week
- **Target**: 90% of trading operations performed via UI (vs API/CLI) after 1 month
- **Target**: Average session duration >10 minutes (indicates engagement)

### Performance Metrics
- **Target**: Initial page load <3 seconds (desktop, broadband)
- **Target**: Time to interactive <2 seconds
- **Target**: API response time <500ms (95th percentile)
- **Target**: Zero data loss during session (no accidental logouts)

### Reliability Metrics
- **Target**: 99.9% uptime (excluding planned maintenance)
- **Target**: <1% error rate on API requests (excluding network issues)
- **Target**: Successful token refresh rate >99%

### User Experience Metrics
- **Target**: <5 clicks to execute a manual trade
- **Target**: <3 clicks to toggle automation
- **Target**: Zero critical UI bugs in production
- **Target**: <2 second delay for position updates to reflect in UI

### Business Metrics
- **Target**: 50% reduction in support tickets related to trading operations
- **Target**: 20% increase in manual trading frequency (indicates UI makes it easier)
- **Target**: 100% feature parity with API by end of phase 1

## Open Questions

1. **Multi-Account API Support**: Does the current API support querying multiple accounts, or do we need to make multiple sequential requests?
   - *Impact*: Affects implementation of combined account view

2. **Strategy Control Granularity**: Can individual strategies be enabled/disabled via the API, or is it all-or-nothing automation?
   - *Impact*: Affects automation control UI design

3. **Historical Data Availability**: Does the API provide historical position/trade data, or only current positions?
   - *Impact*: Affects analytics dashboard implementation

4. **Trade History**: Is there an endpoint for closed positions/trade history?
   - *Impact*: Required for calculating performance metrics

5. **Configuration Update Permissions**: Should all users be able to update system configuration, or only admin users?
   - *Impact*: May require role-based UI adjustments

6. **Position Modification**: Can stop loss and take profit be modified after position is opened via the API?
   - *Impact*: Affects position management UI features

7. **Symbol List**: Where should the list of tradeable symbols come from? Hardcoded, from API, or configuration file?
   - *Impact*: Affects trade entry form implementation

8. **Error Message Standardization**: Are API error messages user-friendly, or do they need to be translated/mapped in the frontend?
   - *Impact*: Affects error handling implementation

9. **Deployment Environment**: Will this be deployed on Vercel/Netlify, or self-hosted on Docker?
   - *Impact*: Affects build configuration and environment setup

10. **Analytics Data Source**: Should performance metrics be calculated client-side from position data, or does the API provide pre-calculated analytics?
    - *Impact*: Affects implementation complexity and accuracy

---

## Implementation Phases (Suggested)

**Phase 1: MVP (Weeks 1-4)**
- FR1: Authentication system
- FR2: Basic dashboard layout
- FR3: Position monitoring (read-only)
- FR5: Basic automation toggle
- FR9: System status display

**Phase 2: Core Trading (Weeks 5-8)**
- FR4: Manual trading interface
- FR3: Enhanced position management (modify, close)
- FR11: Comprehensive error handling
- FR12: Performance optimizations

**Phase 3: Analytics & Multi-Account (Weeks 9-12)**
- FR6: Account analytics dashboard
- FR7: Risk management dashboard
- FR8: Multi-account support
- FR10: Configuration management

---

## Appendix: API Endpoint Mapping

| Feature | API Endpoint | Method | Purpose |
|---------|-------------|--------|---------|
| Login | `/auth/login` | POST | Authenticate user |
| Refresh Token | `/auth/refresh` | POST | Refresh access token |
| Validate Token | `/auth/me` | GET | Validate current token |
| Get Positions | `/positions` | GET | Fetch all open positions |
| Get Single Position | `/positions/{id}` | GET | Fetch position details |
| Get Position Summary | `/positions/summary` | GET | Aggregated position data |
| Entry Signal | `/signals/entry` | POST | Open new position |
| Exit Signal | `/signals/exit` | POST | Close position |
| Automation Status | `/automation/status` | GET | Check automation state |
| Enable Automation | `/automation/enable` | POST | Enable automated trading |
| Disable Automation | `/automation/disable` | POST | Disable automated trading |
| Get Account | `/account` | GET | Fetch account info |
| Get Account Balance | `/account/balance` | GET | Fetch balance |
| Get Account Equity | `/account/equity` | GET | Fetch equity |
| Get Indicators | `/indicators` | GET | Fetch indicator data |
| Get Strategies | `/strategies` | GET | Fetch strategy list |
| Get Risk Status | `/risk/status` | GET | Fetch risk metrics |
| Get Risk Daily | `/risk/daily` | GET | Daily risk data |
| Get Config | `/config` | GET | Fetch configuration |
| Update Config | `/config` | PUT | Update configuration |
| System Status | `/system/status` | GET | System health |
| System Metrics | `/system/metrics` | GET | Detailed metrics |
| Health Check | `/health` | GET | API health check |

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: AI Assistant
**Stakeholder**: Quantronaute Trading Platform Team
