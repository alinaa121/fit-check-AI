import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService, AgentResponse, OutfitCombination, ClothingItemEnriched } from '../../services/chat.service';

interface Message {
  type: 'user' | 'agent';
  query: string;
  input: string; // The user's original input/query string
  response?: AgentResponse;
  timestamp: Date;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css']
})
export class ChatComponent implements OnInit {
  messages: Message[] = [];
  userInput = '';
  loading = false;
  error: string | null = null;
  currentLoadingMessage = '';

  private readonly loadingMessages = [
    'Searching your wardrobe...',
    'Finding the perfect combo...',
    'Mixing & matching...',
    'Unleashing the style magic...',
    'Curating your look...',
    'Working my fashion magic...',
    'Putting together something fabulous...'
  ];

  private readonly celebrationMessages = [
    'Here are your fabulous looks!',
    'Check out these amazing combos!',
    'Perfect! I found some stunning options!',
    'Your style is coming together beautifully!',
    'These looks are amazing!'
  ];

  private readonly encouragementMessages = [
    'Try a different description!',
    'Maybe try specific colors or occasions?',
    'How about mentioning a style or vibe?',
    'Want to try another search?'
  ];

  constructor(private chatService: ChatService) {}

  ngOnInit() {
    // Initialize with a welcome message
    this.messages.push({
      type: 'agent',
      query: 'Welcome to Wardrobe AI Chat',
      input: '', // Empty input for welcome message
      response: {
        combinations: [],
        count: 0,
        input: '',
        status: 'success'
      },
      timestamp: new Date()
    });
  }

  private getRandomMessage(messages: string[]): string {
    return messages[Math.floor(Math.random() * messages.length)];
  }

  getLoadingMessage(): string {
    return this.getRandomMessage(this.loadingMessages);
  }

  getCelebrationMessage(): string {
    return this.getRandomMessage(this.celebrationMessages);
  }

  getEncouragementMessage(): string {
    return this.getRandomMessage(this.encouragementMessages);
  }

  sendMessage() {
    if (!this.userInput.trim()) {
      return;
    }

    const userQuery = this.userInput.trim();
    
    // Add user message to chat
    this.messages.push({
      type: 'user',
      query: userQuery,
      input: userQuery,
      timestamp: new Date()
    });

    this.userInput = '';
    this.loading = true;
    this.currentLoadingMessage = this.getLoadingMessage();
    this.error = null;

    // Call the agent
    this.chatService.callAgent(userQuery).subscribe({
      next: (response: AgentResponse) => {
        // Add agent response to chat
        this.messages.push({
          type: 'agent',
          query: userQuery,
          input: userQuery,
          response: response,
          timestamp: new Date()
        });
        this.loading = false;
      },
      error: (err) => {
        this.error = `Error: ${err.error?.detail || err.message || 'Unknown error'}`;
        this.loading = false;
      }
    });
  }

  getItemCategories(combo: OutfitCombination): Array<{ name: string; item: ClothingItemEnriched | null | undefined }> {
    return [
      { name: 'Top', item: combo.top },
      { name: 'Bottom', item: combo.bottom },
      { name: 'Full Body', item: combo.full_body },
      { name: 'Footwear', item: combo.footwear }
    ].filter(cat => cat.item);
  }

  getAccessories(combo: OutfitCombination): ClothingItemEnriched[] {
    return combo.accessories || [];
  }

  trackByIndex(index: number): number {
    return index;
  }

  openImage(imageUrl: string) {
    /**
     * Open image in a new window/tab on click.
     * User can then view full resolution, download, inspect, etc.
     */
    if (imageUrl) {
      window.open(imageUrl, '_blank');
    }
  }
}
