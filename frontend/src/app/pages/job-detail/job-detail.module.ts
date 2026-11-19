import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule, Routes } from '@angular/router';
import { IonicModule } from '@ionic/angular';

import { JobDetailPage } from './job-detail.page';

const routes: Routes = [{ path: '', component: JobDetailPage }];

@NgModule({
  imports: [CommonModule, FormsModule, IonicModule, RouterModule.forChild(routes)],
  declarations: [JobDetailPage],
})
export class JobDetailPageModule {}
