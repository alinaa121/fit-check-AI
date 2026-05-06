import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ChatService, AgentResponse, OutfitCombination, ClothingItemEnriched } from '../../services/chat.service';

interface Message {
  type: 'user' | 'agent';
  query: string;
  input: string; // The user's original input/query string
  response?: AgentResponse;
  renderedMarkdown?: SafeHtml; // Rendered markdown with hover tooltips
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

  private readonly loadingMessages = ['...'];

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

  constructor(private chatService: ChatService, private sanitizer: DomSanitizer) {}

  ngOnInit() {
    // Initialize with a welcome message
    const welcomeMarkdown = `Hi! I'm your AI fashion stylist. How can I help you style today? Want outfit ideas, styling tips, or something else? 💕`;

    this.messages.push({
      type: 'agent',
      query: 'Welcome to Wardrobe AI Chat',
      input: '',
      response: {
        combinations: [],
        count: 0,
        input: '',
        agent_response: welcomeMarkdown,
        status: 'success'
      },
      renderedMarkdown: this.parseMarkdownWithHover(welcomeMarkdown),
      timestamp: new Date()
    });
  }

  private getRandomMessage(messages: string[]): string {
    return messages[Math.floor(Math.random() * messages.length)];
  }

  /**
   * Parse markdown and convert links with image URLs to hover tooltips
   * Converts: [item_name](image_url) to clickable links with image hover
   */
  parseMarkdownWithHover(markdown: string): SafeHtml {
    let html = markdown;
    
    // Escape HTML first
    html = html
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
    
    // Convert bold **text** to <strong>text</strong>
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic *text* to <em>text</em> (be careful not to match **)
    html = html.replace(/(?<!\*)\*(.*?)\*(?!\*)/g, '<em>$1</em>');
    
    // Convert headers ## text to <h3>text</h3>
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    
    // Convert bullet points - text or * text
    html = html.replace(/^[\-\*] (.*?)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>)/s, '<ul>$1</ul>');
    html = html.replace(/<\/ul>\n<ul>/g, ''); // Remove duplicate ul tags
    
    // Convert markdown links [text](url) to links with hover image tooltips
    // Pattern: [item_name](http://localhost:8000/wardrobe/image/...)
    html = html.replace(
      /\[(.*?)\]\((http:\/\/localhost:8000\/wardrobe\/image\/.*?)\)/g,
      (match, itemName, imageUrl) => {
        return `<span class="markdown-link" data-image="${imageUrl}"><u>${itemName}</u></span>`;
      }
    );
    
    // Convert line breaks
    html = html.replace(/\n/g, '<br>');
    
    return this.sanitizer.bypassSecurityTrustHtml(html);
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
        // Parse markdown response with hover image tooltips
        const renderedMarkdown = this.parseMarkdownWithHover(response.agent_response);
        
        // Add agent response to chat
        this.messages.push({
          type: 'agent',
          query: userQuery,
          input: userQuery,
          response: response,
          renderedMarkdown: renderedMarkdown,
          timestamp: new Date()
        });
        this.loading = false;
        
        // Attach hover listeners after rendering
        setTimeout(() => this.attachHoverListeners(), 100);
      },
      error: (err) => {
        this.error = `Error: ${err.error?.detail || err.message || 'Unknown error'}`;
        this.loading = false;
      }
    });
  }

  /**
   * Attach hover event listeners to markdown links for image tooltips
   */
  attachHoverListeners() {
    const links = document.querySelectorAll('.markdown-link');
    console.log('Attaching hover listeners to', links.length, 'links');
    links.forEach((link: Element, index) => {
      const imageUrl = link.getAttribute('data-image');
      console.log('Link', index, 'URL:', imageUrl);
      if (imageUrl) {
        link.addEventListener('mouseenter', (e) => {
          console.log('Hovering over link:', imageUrl);
          this.showImageTooltip(e, imageUrl);
        });
        
        link.addEventListener('mouseleave', () => {
          console.log('Left link');
          this.hideImageTooltip();
        });
        
        link.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
        });
      }
    });
  }

  /**
   * Show image tooltip on hover
   */
  showImageTooltip(event: Event, imageUrl: string) {
    console.log('Showing tooltip for:', imageUrl);
    // Remove any existing tooltip
    this.hideImageTooltip();
    
    const element = event.target as HTMLElement;
    const tooltip = document.createElement('div');
    tooltip.id = 'image-tooltip';
    tooltip.className = 'image-tooltip';
    
    // Force styles directly
    tooltip.style.cssText = `
      position: fixed !important;
      background: white !important;
      border: 3px solid #e91e8c !important;
      border-radius: 12px !important;
      padding: 12px !important;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3) !important;
      z-index: 99999 !important;
      max-width: 260px !important;
      max-height: 350px !important;
      display: block !important;
      visibility: visible !important;
      opacity: 1 !important;
    `;
    
    // Create image element
    const img = document.createElement('img');
    img.className = 'tooltip-image';
    img.src = imageUrl;
    img.alt = 'Item preview';
    img.style.cssText = `
      width: 100% !important;
      height: auto !important;
      max-height: 330px !important;
      border-radius: 8px !important;
      object-fit: contain !important;
      display: block !important;
    `;
    img.onload = () => console.log('Image loaded successfully');
    img.onerror = () => console.log('Failed to load image:', imageUrl);
    
    tooltip.appendChild(img);
    document.body.appendChild(tooltip);
    console.log('Tooltip created and appended to body');

    // Position tooltip near mouse, centered horizontally
    const rect = element.getBoundingClientRect();
    const tooltipWidth = 260;
    let left = rect.left + rect.width / 2 - tooltipWidth / 2;
    let top = rect.bottom + 15;
    
    // Keep tooltip within viewport
    if (left < 10) left = 10;
    if (left + tooltipWidth > window.innerWidth - 10) {
      left = window.innerWidth - tooltipWidth - 10;
    }
    
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
    console.log('Positioned at LEFT:', left, 'TOP:', top, 'Window size:', window.innerWidth, 'x', window.innerHeight);
  }

  /**
   * Hide image tooltip
   */
  hideImageTooltip() {
    const tooltip = document.getElementById('image-tooltip');
    if (tooltip) {
      tooltip.remove();
    }
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
