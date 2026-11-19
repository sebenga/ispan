import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

/** Guest-only: if already logged in, go to the matching dashboard. */
export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const user = auth.currentUser;
  if (!user) return true;
  return router.createUrlTree([user.role === 'WORKER' ? '/worker' : '/customer']);
};
