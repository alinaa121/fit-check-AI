import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface ClothingItem {
  id: string;
  image_url: string;
  image_url_no_bg: string;
  img_path: string;
  raw_caption: string;
  primary_category: string;
  sub_category: string;
  primary_color: string;
  secondary_colors: string[];
  pattern: string;
  material: string;
  season: string[];
  weather: string[];
  occasion: string[];
  fit: string;
  style_vibe: string[];
  created_at: string;
  modified_at: string;
  score?: number; // Similarity score for search results
}

export interface RecommendationResponse {
  caption: string;
  items: string[]; // Array of image URLs
}

@Injectable({
  providedIn: 'root'
})
export class WardrobeService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  getAllItems(limit: number = 100): Observable<ClothingItem[]> {
    return this.http.get<ClothingItem[]>(`${this.apiUrl}/wardrobe/items?limit=${limit}`);
  }

  searchItems(query: string, limit: number = 10): Observable<ClothingItem[]> {
    return this.http.get<ClothingItem[]>(`${this.apiUrl}/wardrobe/search?query=${query}&limit=${limit}`);
  }

  getItem(itemId: string): Observable<ClothingItem> {
    return this.http.get<ClothingItem>(`${this.apiUrl}/wardrobe/item/${itemId}`);
  }

  uploadItem(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.apiUrl}/wardrobe/upload`, formData);
  }

  deleteItem(itemId: string): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/wardrobe/item/${itemId}`);
  }

  updateItem(itemId: string, fieldName: string, newValue: any): Observable<any> {
    return this.http.patch<any>(`${this.apiUrl}/wardrobe/item/${itemId}`, {
      field_name: fieldName,
      new_value: newValue
    });
  }

  recommendItems(query: string): Observable<RecommendationResponse> {
    return this.http.get<any>(`${this.apiUrl}/wardrobe/search?query=${query}`).pipe(
      // Transform full URLs to match expected response format
      map((response: any) => ({
        caption: response.caption,
        items: response.items || []  // Already full URLs from /search endpoint
      }))
    );
  }

  getOutfitFeedback(itemIds: string[], context?: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/wardrobe/outfit-feedback`, {
      item_ids: itemIds,
      context: context || null
    });
  }

  saveOutfit(itemIds: string[], outfitName?: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/wardrobe/outfit-save`, {
      item_ids: itemIds,
      name: outfitName || null
    });
  }

  getOutfits(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/wardrobe/outfits`);
  }

  deleteOutfit(outfitId: string): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/wardrobe/outfit-delete/${outfitId}`);
  }
}
