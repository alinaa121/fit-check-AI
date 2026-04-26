import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WardrobeService, ClothingItem } from '../../services/wardrobe.service';

@Component({
  selector: 'app-wardrobe',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './wardrobe.component.html',
  styleUrls: ['./wardrobe.component.css']
})
export class WardrobeComponent implements OnInit {
  items: ClothingItem[] = [];
  loading = true;
  error: string | null = null;
  selectedItem: ClothingItem | null = null;
  uploading = false;
  uploadError: string | null = null;
  showUploadZone = false;
  dragOver = false;
  deleting = false;
  editMode = false;
  editingField: string | null = null;
  editValue: any = null;
  saving = false;
  
  // Filter properties
  categories = ['All', 'Top', 'Bottom', 'Outerwear', 'Footwear', 'Accessory', 'Full-body'];
  selectedCategory = 'All';

  // Allowed values for dropdowns (from config.py enums)
  patternOptions = ['Solid', 'Striped', 'Check', 'Floral', 'Graphic', 'Geometric', 'Animal Print', 'Houndstooth', 'Camo', 'Other'];
  materialOptions = ['Cotton', 'Denim', 'Leather', 'Wool', 'Linen', 'Silk', 'Synthetic', 'Knit', 'Velvet', 'Suede', 'Other'];
  fitOptions = ['Slim', 'Regular', 'Oversized', 'Tailored', 'Cropped', 'Other'];
  colorOptions = ['Black', 'White', 'Grey', 'Navy', 'Blue', 'Red', 'Green', 'Yellow', 'Orange', 'Purple', 'Pink', 'Brown', 'Beige', 'Gold', 'Silver', 'Multicolor'];
  seasonOptions = ['Spring', 'Summer', 'Fall', 'Winter', 'All-Season'];
  occasionOptions = ['Casual', 'Smart-Casual', 'Business-Formal', 'Athletic/Gym', 'Lounge', 'Night-Out', 'Formal/Black-Tie'];
  styleVibeOptions = ['Minimalist', 'Streetwear', 'Vintage/Retro', 'Preppy', 'Grunge', 'Techwear', 'Bohemian', 'Classic', 'Other'];

  constructor(private wardrobeService: WardrobeService) {}

  ngOnInit() {
    this.loadItems();
  }

  loadItems() {
    this.loading = true;
    this.error = null;
    
    this.wardrobeService.getAllItems().subscribe({
      next: (items) => {
        this.items = items;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load wardrobe items. Make sure the API is running.';
        this.loading = false;
        console.error('Error loading items:', err);
      }
    });
  }

  selectItem(item: ClothingItem) {
    this.selectedItem = item;
  }

  closeModal() {
    this.selectedItem = null;
    this.editMode = false;
    this.editingField = null;
    this.editValue = null;
  }

  toggleEditMode() {
    this.editMode = !this.editMode;
    if (!this.editMode) {
      this.editingField = null;
      this.editValue = null;
    }
  }

  startEditing(fieldName: string, currentValue: any) {
    this.editingField = fieldName;
    this.editValue = Array.isArray(currentValue) ? [...currentValue] : currentValue;
  }

  cancelEditing() {
    this.editingField = null;
    this.editValue = null;
  }

  saveField() {
    if (!this.selectedItem || !this.editingField) return;

    this.saving = true;
    const fieldName = this.editingField;
    const newValue = this.editValue;

    this.wardrobeService.updateItem(this.selectedItem.id, fieldName, newValue).subscribe({
      next: (response) => {
        console.log('Update successful:', response);
        this.saving = false;
        
        // Update the selected item with new value
        if (this.selectedItem) {
          (this.selectedItem as any)[fieldName] = newValue;
          
          // Also update in the items array
          const index = this.items.findIndex(i => i.id === this.selectedItem!.id);
          if (index !== -1) {
            (this.items[index] as any)[fieldName] = newValue;
          }
        }
        
        this.editingField = null;
        this.editValue = null;
      },
      error: (err) => {
        console.error('Update error:', err);
        this.saving = false;
        alert('Failed to update: ' + (err.error?.detail || 'Unknown error'));
      }
    });
  }

  getColorBadge(color: string): string {
    const colorMap: { [key: string]: string } = {
      'Black': '#000000',
      'White': '#FFFFFF',
      'Grey': '#9CA3AF',
      'Navy': '#1E40AF',
      'Blue': '#3B82F6',
      'Red': '#EF4444',
      'Green': '#10B981',
      'Yellow': '#FBBF24',
      'Orange': '#F97316',
      'Purple': '#A855F7',
      'Pink': '#EC4899',
      'Brown': '#92400E',
      'Beige': '#D4B896',
      'Gold': '#FCD34D',
      'Silver': '#CBD5E1'
    };
    return colorMap[color] || '#9CA3AF';
  }

  // Filter methods
  selectCategory(category: string) {
    this.selectedCategory = category;
  }

  get filteredItems(): ClothingItem[] {
    if (this.selectedCategory === 'All') {
      return this.items;
    }
    return this.items.filter(item => item.primary_category === this.selectedCategory);
  }

  toggleUploadZone() {
    this.showUploadZone = !this.showUploadZone;
    this.uploadError = null;
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadFile(input.files[0]);
    }
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver = false;

    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      this.uploadFile(event.dataTransfer.files[0]);
    }
  }

  uploadFile(file: File) {
    // Validate file type
    if (!file.type.startsWith('image/')) {
      this.uploadError = 'Please upload an image file';
      return;
    }

    this.uploading = true;
    this.uploadError = null;

    this.wardrobeService.uploadItem(file).subscribe({
      next: (response) => {
        console.log('Upload successful:', response);
        this.uploading = false;
        this.showUploadZone = false;
        
        if (response.status === 'success') {
          // Reload items to show the new upload
          this.loadItems();
        } else if (response.status === 'rejected') {
          this.uploadError = response.message || 'Image was rejected';
        }
      },
      error: (err) => {
        console.error('Upload error:', err);
        this.uploading = false;
        this.uploadError = err.error?.detail || 'Failed to upload image. Please try again.';
      }
    });
  }

  deleteItem(item: ClothingItem) {
    // Show confirmation dialog
    const confirmed = window.confirm(
      `Are you sure you want to delete this ${item.sub_category}?\n\n"${item.raw_caption}"\n\nThis action cannot be undone.`
    );

    if (!confirmed) {
      return;
    }

    this.deleting = true;

    this.wardrobeService.deleteItem(item.id).subscribe({
      next: (response) => {
        console.log('Delete successful:', response);
        this.deleting = false;
        this.closeModal();
        
        // Remove item from local array
        this.items = this.items.filter(i => i.id !== item.id);
      },
      error: (err) => {
        console.error('Delete error:', err);
        this.deleting = false;
        alert('Failed to delete item: ' + (err.error?.detail || 'Unknown error'));
      }
    });
  }

  // Array editing helpers
  addToArray(item: string) {
    if (!Array.isArray(this.editValue)) {
      this.editValue = [];
    }
    if (!this.editValue.includes(item) && this.editValue.length < 3) {
      this.editValue.push(item);
    }
  }

  removeFromArray(item: string) {
    if (Array.isArray(this.editValue)) {
      this.editValue = this.editValue.filter(v => v !== item);
    }
  }

  canAddToArray(): boolean {
    return Array.isArray(this.editValue) && this.editValue.length < 3;
  }

  getAvailableOptions(fieldName: string): string[] {
    const allOptions = this.getOptionsForField(fieldName);
    if (!Array.isArray(this.editValue)) {
      return allOptions;
    }
    return allOptions.filter(option => !this.editValue.includes(option));
  }

  getOptionsForField(fieldName: string): string[] {
    switch (fieldName) {
      case 'primary_color':
      case 'secondary_colors':
        return this.colorOptions;
      case 'season':
        return this.seasonOptions;
      case 'occasion':
        return this.occasionOptions;
      case 'style_vibe':
        return this.styleVibeOptions;
      default:
        return [];
    }
  }
}
