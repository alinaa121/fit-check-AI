import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ClothingItemEnriched {
  id: string;
  description: string;
  link: string;
  raw_caption?: string;
  primary_category?: string;
  primary_color?: string;
}

export interface OutfitCombination {
  combo_id: number;
  top?: ClothingItemEnriched | null;
  bottom?: ClothingItemEnriched | null;
  full_body?: ClothingItemEnriched | null;
  footwear?: ClothingItemEnriched | null;
  accessories?: ClothingItemEnriched[];
  reasoning?: string;
  style_tips?: string;
}

export interface AgentResponse {
  combinations?: OutfitCombination[];
  count?: number;
  input: string;
  status: string;
  agent_response: string; // Markdown text response from agent
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  /**
   * Call the wardrobe agent with a natural language query.
   * Returns markdown text response with embedded image links.
   */
  callAgent(query: string): Observable<AgentResponse> {
    return this.http.post<AgentResponse>(`${this.apiUrl}/wardrobe/agent?query=${encodeURIComponent(query)}`, {});
  }
}
