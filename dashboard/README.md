# Universal Testing Platform Dashboard v2.2.0

Dashboard UI for the Universal Testing Platform, built with Next.js, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, and Recharts.

## Features

- **Platform Overview**: View platform-wide metrics including total projects, active projects, total runs, failing projects, flaky projects, quality gate overview, and plugin usage
- **AI QA Command Center**: Executive quality command-center view backed by local intelligence artifacts (`release_decision.json`, `dashboard_snapshot.json`, `defect_cluster_report.json`, `autonomous_rerun_plan.json`)
- **Projects List**: Browse all projects with search, filter by product type, filter by gate result, and sorting
- **Project Detail**: View project metadata, summary, trend charts, flaky summary, compatibility, and latest runs
- **Runs Explorer**: Explore test runs across all projects with status, duration, timestamps, and artifacts
- **Plugin Catalog**: Browse available plugins with support level, capabilities, compatibility notes, and onboarding completeness

## Prerequisites

- Node.js 18+ installed
- Python 3.8+ installed (for the backend API)
- The Universal Testing Platform backend API running on `http://localhost:8000`

## Installation

1. Navigate to the dashboard directory:
   ```bash
   cd dashboard
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Running the Dashboard

1. Start the backend API (from the repository root):
   ```bash
   # In a terminal
   uvicorn api.app:app --reload
   ```

2. Start the dashboard (in another terminal):
   ```bash
   # From the dashboard directory
   npm run dev
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```
4. Open AI QA Command Center:
   ```
   http://localhost:3000/qa-command-center
   ```

### AI QA Command Center Artifact Inputs

The command center page reads artifact JSON files from the repository root (`../` relative to `dashboard/`) and renders fallback cards when data is unavailable:

- `release_decision.json`
- `dashboard_snapshot.json`
- `defect_cluster_report.json`
- `autonomous_rerun_plan.json`

## Environment Variables

Create a `.env.local` file in the dashboard directory to configure the API URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Building for Production

```bash
npm run build
npm start
```

## Tech Stack

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: Beautiful, accessible component library
- **TanStack Query**: Data fetching and state management
- **Recharts**: Chart library for data visualization
- **Lucide React**: Icon library
- **date-fns**: Date manipulation library

## Project Structure

```
dashboard/
├── app/                    # Next.js app directory
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout with sidebar
│   ├── page.tsx           # Platform overview page
│   ├── projects/          # Projects pages
│   │   ├── page.tsx       # Projects list
│   │   └── [id]/page.tsx  # Project detail
│   ├── runs/              # Runs explorer page
│   └── plugins/           # Plugin catalog page
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   │   ├── card.tsx
│   │   └── button.tsx
│   └── sidebar.tsx       # Sidebar navigation
├── lib/                   # Utility functions
│   ├── api-client.ts     # API client for backend
│   ├── types.ts          # TypeScript types
│   └── utils.ts          # Utility functions
├── package.json           # Dependencies
├── tsconfig.json         # TypeScript config
├── tailwind.config.ts    # Tailwind config
└── postcss.config.js     # PostCSS config
```

## API Integration

The dashboard communicates with the backend API using the following endpoints:

- `GET /health/` - Health check
- `GET /platform/summary` - Platform-wide summary
- `GET /platform/projects/latest` - Latest project status
- `GET /projects/` - List projects
- `GET /projects/{id}` - Get project details
- `POST /projects/{id}/run` - Trigger a run
- `GET /projects/{id}/runs` - List project runs
- `GET /projects/{id}/summary` - Get project summary
- `GET /projects/{id}/trends` - Get project trends
- `GET /plugins/` - List plugins
- `GET /plugins/{name}` - Get plugin details
- `GET /plugins/{name}/compatibility` - Get plugin compatibility

## Windows-Specific Notes

- The dashboard works on Windows with no special configuration
- Use PowerShell or Command Prompt to run commands
- If you encounter issues with long paths, consider enabling long path support in Windows

## Development

```bash
# Run in development mode
npm run dev

# Run linter
npm run lint

# Build for production
npm run build
```

## License

Same as the Universal Testing Platform.
