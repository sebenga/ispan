import { NgModule } from '@angular/core';
import { PreloadAllModules, RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  {
    path: 'login',
    loadChildren: () => import('./pages/login/login.module').then((m) => m.LoginPageModule),
  },
  {
    path: 'register',
    loadChildren: () =>
      import('./pages/register/register.module').then((m) => m.RegisterPageModule),
  },
  {
    path: 'customer',
    loadChildren: () =>
      import('./pages/customer/customer.module').then((m) => m.CustomerPageModule),
  },
  {
    path: 'customer/new',
    loadChildren: () =>
      import('./pages/post-job/post-job.module').then((m) => m.PostJobPageModule),
  },
  {
    path: 'customer/jobs/:id',
    loadChildren: () =>
      import('./pages/job-detail/job-detail.module').then((m) => m.JobDetailPageModule),
  },
  {
    path: 'worker',
    loadChildren: () => import('./pages/worker/worker.module').then((m) => m.WorkerPageModule),
  },
  {
    path: 'worker/jobs/:id',
    loadChildren: () =>
      import('./pages/job-detail/job-detail.module').then((m) => m.JobDetailPageModule),
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { preloadingStrategy: PreloadAllModules })],
  exports: [RouterModule],
})
export class AppRoutingModule {}
