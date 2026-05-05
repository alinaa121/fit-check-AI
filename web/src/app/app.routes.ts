import { Routes } from '@angular/router';
import { WelcomeComponent } from './pages/welcome/welcome.component';
import { WardrobeComponent } from './pages/wardrobe/wardrobe.component';
import { ChatComponent } from './pages/chat/chat.component';

export const routes: Routes = [
  { path: '', component: WelcomeComponent },
  { path: 'wardrobe', component: WardrobeComponent },
  { path: 'chat', component: ChatComponent },
  { path: '**', redirectTo: '' }
];
