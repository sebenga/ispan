import { Routes } from '@angular/router';

import { legalGuard } from './core/legal.guard';
import { guestGuard } from './core/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'legal',
  },
  {
    path: 'legal',
    loadComponent: () =>
      import('./pages/legal-gate/legal-gate.page').then((m) => m.LegalGatePage),
  },
  {
    path: 'legal/terms',
    loadComponent: () =>
      import('./pages/legal-doc/legal-doc.page').then((m) => m.LegalDocPage),
    data: { slug: 'terms' },
  },
  {
    path: 'legal/privacy',
    loadComponent: () =>
      import('./pages/legal-doc/legal-doc.page').then((m) => m.LegalDocPage),
    data: { slug: 'privacy' },
  },
  {
    path: 'legal/notice',
    loadComponent: () =>
      import('./pages/legal-doc/legal-doc.page').then((m) => m.LegalDocPage),
    data: { slug: 'notice' },
  },
  {
    path: 'login',
    canActivate: [legalGuard, guestGuard],
    loadComponent: () => import('./pages/login/login.page').then((m) => m.LoginPage),
  },
  {
    path: 'register',
    canActivate: [legalGuard],
    loadComponent: () =>
      import('./pages/register/register.page').then((m) => m.RegisterPage),
  },
  {
    path: 'otp',
    canActivate: [legalGuard],
    loadComponent: () => import('./pages/otp/otp.page').then((m) => m.OtpPage),
  },
  {
    path: 'worker/onboarding',
    canActivate: [legalGuard],
    loadComponent: () =>
      import('./pages/worker-onboarding/worker-onboarding.page').then(
        (m) => m.WorkerOnboardingPage,
      ),
  },
  {
    path: 'admin/verification',
    canActivate: [legalGuard],
    loadComponent: () =>
      import('./pages/admin-verification/admin-verification.page').then(
        (m) => m.AdminVerificationPage,
      ),
  },
  {
    path: 'customer',
    canActivate: [legalGuard],
    loadComponent: () =>
      import('./pages/customer/customer.page').then((m) => m.CustomerPage),
  },
  {
    path: 'customer/new',
    canActivate: [legalGuard],
    loadComponent: () =>
      import('./pages/post-job/post-job.page').then((m) => m.PostJobPage),
  },
  {
    path: 'customer/jobs/:id',
    canActivate: [legalGuard],
    loadComponent: () =>
      import('./pages/job-detail/job-detail.page').then((m) => m.JobDetailPage),
  },
  {
    path: 'worker',
    canActivate: [legalGuard],
    loadComponent: () => import('./pages/worker/worker.page').then((m) => m.WorkerPage),
  },
  {
    path: 'worker/jobs/:id',
    canActivate: [legalGuard],
    loadComponent: () =>
      import('./pages/job-detail/job-detail.page').then((m) => m.JobDetailPage),
  },
  { path: '**', redirectTo: 'legal' },
];
