import React from 'react';
import { ShieldCheck, LogOut } from 'lucide-react';
import PilotReviewPanel from './PilotReviewPanel';
import { Button } from './ui/button';

const PilotReviewPage = ({ user, onLogout }) => {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-card/60 backdrop-blur-sm sticky top-0 z-20">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">Pilot Review</h1>
              <p className="text-sm text-muted-foreground">Manual live pilot readiness, reconciliation, reports, and signoff controls.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {user?.email && <span className="hidden md:inline text-sm text-muted-foreground">{user.email}</span>}
            <Button variant="outline" size="sm" onClick={onLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <PilotReviewPanel />
      </main>
    </div>
  );
};

export default PilotReviewPage;
