import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WardrobeService, ClothingItem } from '../../services/wardrobe.service';

@Component({
  selector: 'app-wardrobe',
  standalone: true,
  imports: [CommonModule],
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
  
  // Filter properties
  categories = ['All', 'Top', 'Bottom', 'Outerwear', 'Footwear', 'Accessory', 'Full-body'];
  selectedCategory = 'All';

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
}
