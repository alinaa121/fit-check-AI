import { Routes } from '@angular/router';
import { WelcomeComponent } from './pages/welcome/welcome.component';
import { WardrobeComponent } from './pages/wardrobe/wardrobe.component';

export const routes: Routes = [
  { path: '', component: WelcomeComponent },
  { path: 'wardrobe', component: WardrobeComponent },
  { path: '**', redirectTo: '' }
];
