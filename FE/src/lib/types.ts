export interface Song {
    song_id: number;
    song_name: string;
    artist: string;
    genre?: string;
}

export interface RecommendationItem extends Song {
    rank: number;
    score: number;
}

export interface RecommendResponse {
    engine_version: string;
    audio_model: string;
    cached: boolean;
    method: string;
    seed: Song;
    items: RecommendationItem[];
}
