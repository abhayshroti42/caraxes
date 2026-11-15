import { Link, Outlet } from "react-router-dom";

export default function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/gallery" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">C</span>
            <span className="text-lg font-bold text-gray-900">Caraxes</span>
            <span className="hidden text-sm text-gray-500 sm:inline">Public gallery</span>
          </Link>
          <Link to="/" className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">
            Open workspace →
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-gray-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-gray-500">
          Sessions shown here were published by their owning companies after review. Brand guidelines,
          internal rules and review notes are never displayed.
        </div>
      </footer>
    </div>
  );
}