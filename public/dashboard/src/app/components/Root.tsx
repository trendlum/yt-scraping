import { Outlet, NavLink } from 'react-router';
import { GlobalFilterBar } from './GlobalFilterBar';
import { FilterProvider } from '../contexts/FilterContext';

export function Root() {
  return (
    <FilterProvider>
      <div className="min-h-screen flex flex-col bg-background">
        <header className="sticky top-0 z-50 border-b border-border bg-card">
          <div className="px-6 py-3">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center">
                <img
                  src="/images/transparent_logo_with_name.png"
                  alt="TrendLum"
                  className="block h-6 w-auto max-h-6 object-contain"
                />
              </div>
              <nav className="flex gap-1">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded text-xs transition ${
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:text-primary hover:bg-muted'
                    }`
                  }
                >
                  Overview
                </NavLink>
                <NavLink
                  to="/niches"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded text-xs transition ${
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:text-primary hover:bg-muted'
                    }`
                  }
                >
                  Niches
                </NavLink>
                <NavLink
                  to="/channels"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded text-xs transition ${
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:text-primary hover:bg-muted'
                    }`
                  }
                >
                  Channels
                </NavLink>
                <NavLink
                  to="/topics"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded text-xs transition ${
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:text-primary hover:bg-muted'
                    }`
                  }
                >
                  Topics
                </NavLink>
                <NavLink
                  to="/videos"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded text-xs transition ${
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:text-primary hover:bg-muted'
                    }`
                  }
                >
                  Videos
                </NavLink>
              </nav>
            </div>
          </div>
        </header>

        <GlobalFilterBar />

        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </FilterProvider>
  );
}
