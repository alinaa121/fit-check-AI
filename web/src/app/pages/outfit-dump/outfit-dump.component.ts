import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WardrobeService, ClothingItem } from '../../services/wardrobe.service';

@Component({
  selector: 'app-outfit-dump',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './outfit-dump.component.html',
  styleUrls: ['./outfit-dump.component.css']
})
export class OutfitDumpComponent implements OnInit {
  allClothes: ClothingItem[] = [];
  clothes: ClothingItem[] = [];
  outfitItems: ClothingItem[] = [];
  outfitItemPositions: { [key: number]: { x: number; y: number } } = {};
  outfitItemSizes: { [key: number]: { width: number; height: number } } = {};
  loading = true;
  error: string | null = null;
  draggedItem: ClothingItem | null = null;
  draggedOutfitIndex: number | null = null;
  dragStartPos: { x: number; y: number } = { x: 0, y: 0 };
  feedbackContext: string = '';
  
  // Feedback state
  feedbackLoading = false;
  feedbackText: string | null = null;
  feedbackError: string | null = null;
  
  // Save outfit state
  savingOutfit = false;
  savedRecently = false;
  saveSuccess: string | null = null;
  saveError: string | null = null;
  outfitName: string = '';
  
  // Resizing properties
  isResizing = false;
  resizingIndex: number | null = null;
  resizeStartPos: { x: number; y: number } = { x: 0, y: 0 };
  resizeStartSize: { width: number; height: number } = { width: 0, height: 0 };
  
  categories = ['All', 'Top', 'Bottom', 'Outerwear', 'Footwear', 'Accessory', 'Full-body'];
  selectedCategory = 'All';
  
  // Previous outfits state
  previousOutfits: any[] = [];
  outfitsLoading = false;
  outfitsError: string | null = null;
  expandedOutfitId: string | null = null;

  constructor(private wardrobeService: WardrobeService) {}

  ngOnInit() {
    this.loadClothes();
    this.loadOutfits();
  }

  loadOutfits() {
    this.outfitsLoading = true;
    this.outfitsError = null;
    this.wardrobeService.getOutfits().subscribe({
      next: (response) => {
        this.previousOutfits = response.outfits || [];
        this.outfitsLoading = false;
      },
      error: (err) => {
        this.outfitsError = 'Failed to load previous outfits';
        this.outfitsLoading = false;
        console.error(err);
      }
    });
  }

  loadClothes() {
    this.loading = true;
    this.error = null;
    this.wardrobeService.getAllItems(100).subscribe({
      next: (items) => {
        this.allClothes = items;
        this.filterByCategory();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load clothes. Please try again.';
        this.loading = false;
        console.error(err);
      }
    });
  }

  filterByCategory() {
    if (this.selectedCategory === 'All') {
      this.clothes = this.allClothes;
    } else {
      this.clothes = this.allClothes.filter(
        item => item.primary_category === this.selectedCategory
      );
    }
  }

  onCategoryChange(category: string) {
    this.selectedCategory = category;
    this.filterByCategory();
  }

  onDragStart(event: DragEvent, item: ClothingItem, outfitIndex?: number) {
    this.draggedItem = item;
    if (outfitIndex !== undefined) {
      this.draggedOutfitIndex = outfitIndex;
      // Track starting position for repositioning
      this.dragStartPos = { x: event.clientX || 0, y: event.clientY || 0 };
    }
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'copy';
      event.dataTransfer.setData('application/json', JSON.stringify(item));
    }
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'copy';
    }
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    
    // If dragging from outfit, it's just repositioning - don't remove here
    if (this.draggedOutfitIndex !== null) {
      // Repositioning will be handled by dragend
      return;
    }

    // Handle new items from clothes list
    if (event.dataTransfer) {
      const data = event.dataTransfer.getData('application/json');
      if (data) {
        const item: ClothingItem = JSON.parse(data);
        // Only add if not already in outfit
        if (!this.outfitItems.find(i => i.id === item.id)) {
          const newIndex = this.outfitItems.length;
          this.outfitItems.push(item);
          
          // Calculate position relative to canvas
          const canvas = event.currentTarget as HTMLElement;
          const rect = canvas.getBoundingClientRect();
          const x = (event.clientX || 0) - rect.left - 70;
          const y = (event.clientY || 0) - rect.top - 70;
          
          this.outfitItemPositions[newIndex] = { 
            x: Math.max(0, x), 
            y: Math.max(0, y) 
          };
        }
      }
    }
    this.draggedItem = null;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
  }

  removeFromOutfit(index: number) {
    this.outfitItems.splice(index, 1);
    delete this.outfitItemPositions[index];
    delete this.outfitItemSizes[index];
  }

  clearOutfit() {
    this.outfitItems = [];
    this.outfitItemPositions = {};
    this.outfitItemSizes = {};
  }

  toggleOutfitExpanded(outfitId: string) {
    this.expandedOutfitId = this.expandedOutfitId === outfitId ? null : outfitId;
  }

  deleteOutfit(outfitId: string, event: Event) {
    event.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this outfit?')) {
      return;
    }

    this.wardrobeService.deleteOutfit(outfitId).subscribe({
      next: (response) => {
        // Remove from local list
        this.previousOutfits = this.previousOutfits.filter(
          outfit => outfit.outfit_id !== outfitId
        );
        this.expandedOutfitId = null;
      },
      error: (err) => {
        console.error('Error deleting outfit:', err);
        alert('Failed to delete outfit');
      }
    });
  }

  getOutfitItemStyle(index: number) {
    const pos = this.outfitItemPositions[index] || { x: 0, y: 0 };
    return {
      left: pos.x + 'px',
      top: pos.y + 'px'
    };
  }

  onOutfitItemDragEnd(event: DragEvent, index: number) {
    if (this.draggedOutfitIndex === null) {
      return;
    }

    // Calculate new position based on movement
    const canvas = document.querySelector('.canvas') as HTMLElement;
    if (canvas) {
      const rect = canvas.getBoundingClientRect();
      const newX = (event.clientX || 0) - rect.left - 70;
      const newY = (event.clientY || 0) - rect.top - 70;

      // Only update if within canvas bounds
      if (newX >= 0 && newY >= 0 && newX < rect.width && newY < rect.height) {
        this.outfitItemPositions[index] = {
          x: newX,
          y: newY
        };
      }
    }

    this.draggedOutfitIndex = null;
    this.draggedItem = null;
  }

  onResizeStart(event: MouseEvent, index: number) {
    event.preventDefault();
    event.stopPropagation();
    
    this.isResizing = true;
    this.resizingIndex = index;
    this.resizeStartPos = { x: event.clientX, y: event.clientY };
    
    // Get current size or use default
    const size = this.outfitItemSizes[index] || { width: 140, height: 140 };
    this.resizeStartSize = { ...size };
    
    // Add mouse move and mouse up listeners
    document.addEventListener('mousemove', this.onResizeMove.bind(this));
    document.addEventListener('mouseup', this.onResizeEnd.bind(this));
  }

  onResizeMove(event: MouseEvent) {
    if (!this.isResizing || this.resizingIndex === null) {
      return;
    }

    // Calculate delta from start position
    const deltaX = event.clientX - this.resizeStartPos.x;
    const deltaY = event.clientY - this.resizeStartPos.y;
    
    // Use the larger delta to maintain aspect ratio
    const delta = Math.max(deltaX, deltaY);
    
    // Calculate new size (minimum 80px, maximum 300px)
    const newWidth = Math.max(80, Math.min(300, this.resizeStartSize.width + delta));
    const newHeight = Math.max(80, Math.min(300, this.resizeStartSize.height + delta));
    
    this.outfitItemSizes[this.resizingIndex] = {
      width: newWidth,
      height: newHeight
    };
  }

  onResizeEnd(event: MouseEvent) {
    document.removeEventListener('mousemove', this.onResizeMove.bind(this));
    document.removeEventListener('mouseup', this.onResizeEnd.bind(this));
    
    this.isResizing = false;
    this.resizingIndex = null;
  }

  getOutfitItemSizeStyle(index: number) {
    const size = this.outfitItemSizes[index] || { width: 140, height: 140 };
    return {
      width: size.width + 'px',
      height: size.height + 'px'
    };
  }

  getFeedback() {
    if (this.outfitItems.length === 0) {
      this.feedbackError = 'Please add items to your outfit first';
      this.feedbackText = null;
      return;
    }

    // Reset feedback state
    this.feedbackLoading = true;
    this.feedbackError = null;
    this.feedbackText = null;

    // Extract item IDs from outfit
    const itemIds = this.outfitItems.map(item => item.id);

    // Call the service to get feedback from LLM
    this.wardrobeService.getOutfitFeedback(itemIds, this.feedbackContext).subscribe({
      next: (response) => {
        this.feedbackText = response.feedback;
        this.feedbackLoading = false;
      },
      error: (err) => {
        console.error('Error getting feedback:', err);
        this.feedbackError = 'Failed to generate feedback. Please try again.';
        this.feedbackLoading = false;
      }
    });
  }

  saveOutfit() {
    if (this.outfitItems.length === 0) {
      this.saveError = 'Please add items to your outfit before saving';
      return;
    }

    // Reset save state
    this.savingOutfit = true;
    this.saveError = null;
    this.saveSuccess = null;

    // Extract item IDs
    const itemIds = this.outfitItems.map(item => item.id);

    // Call service to save outfit
    this.wardrobeService.saveOutfit(itemIds, this.outfitName || undefined).subscribe({
      next: (response) => {
        this.saveSuccess = `✓ Outfit "${response.name}" saved successfully!`;
        this.savingOutfit = false;
        this.savedRecently = true;
        this.outfitName = '';
        // Clear success message and re-enable button after 3 seconds
        setTimeout(() => {
          this.saveSuccess = null;
          this.savedRecently = false;
        }, 3000);
      },
      error: (err) => {
        console.error('Error saving outfit:', err);
        this.saveError = 'Failed to save outfit. Please try again.';
        this.savingOutfit = false;
      }
    });
  }
}
