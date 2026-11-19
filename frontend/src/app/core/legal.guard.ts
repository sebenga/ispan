import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { environment } from '../../environments/environment';
import { LegalService } from './legal.service';

export const legalGuard: CanActivateFn = () => {
  const legal = inject(LegalService);
  const router = inject(Router);
  if (legal.hasAccepted(environment.legalVersion)) {
    return true;
  }
  return router.createUrlTree(['/legal']);
};
