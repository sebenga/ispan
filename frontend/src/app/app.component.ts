import { Component } from '@angular/core';
import { IonApp, IonRouterOutlet } from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import {
  alertCircleOutline,
  arrowBackOutline,
  checkmarkCircleOutline,
  constructOutline,
  documentTextOutline,
  flashOutline,
  hammerOutline,
  homeOutline,
  leafOutline,
  locationOutline,
  lockClosedOutline,
  logInOutline,
  personOutline,
  shieldCheckmarkOutline,
  waterOutline,
} from 'ionicons/icons';

addIcons({
  alertCircleOutline,
  arrowBackOutline,
  checkmarkCircleOutline,
  constructOutline,
  documentTextOutline,
  flashOutline,
  hammerOutline,
  homeOutline,
  leafOutline,
  locationOutline,
  lockClosedOutline,
  logInOutline,
  personOutline,
  shieldCheckmarkOutline,
  waterOutline,
});

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [IonApp, IonRouterOutlet],
  template: `<ion-app><ion-router-outlet></ion-router-outlet></ion-app>`,
})
export class AppComponent {}
