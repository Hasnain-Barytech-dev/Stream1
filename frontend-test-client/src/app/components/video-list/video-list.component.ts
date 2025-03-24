// frontend-test-client/src/app/components/video-list/video-list.component.ts
import { Component, OnInit, Input } from '@angular/core';
import { VideoService } from '../../services/video.service';
import { Video } from '../../models/video.model';

@Component({
  selector: 'app-video-list',
  templateUrl: './video-list.component.html',
  styleUrls: ['./video-list.component.scss']
})
export class VideoListComponent implements OnInit {
  @Input() companyId: string | null = null;
  
  videos: Video[] = [];
  loading = true;
  error: string | null = null;
  
  private skip = 0;
  private limit = 20;
  private hasMoreVideos = true;

  constructor(private videoService: VideoService) { }

  ngOnInit(): void {
    this.loadVideos();
  }

  loadVideos(refresh: boolean = false): void {
    if (refresh) {
      this.skip = 0;
      this.videos = [];
      this.hasMoreVideos = true;
    }
    
    this.loading = true;
    this.error = null;
    
    const request = this.companyId
      ? this.videoService.listCompanyVideos(this.companyId, this.skip, this.limit)
      : this.videoService.listMyVideos(this.skip, this.limit);
      
    request.subscribe({
      next: (videos) => {
        this.videos = [...this.videos, ...videos];
        this.hasMoreVideos = videos.length === this.limit;
        this.skip += videos.length;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading videos:', err);
        this.error = 'Failed to load videos';
        this.loading = false;
      }
    });
  }

  loadMore(): void {
    if (this.hasMoreVideos && !this.loading) {
      this.loadVideos();
    }
  }

  deleteVideo(videoId: string): void {
    if (confirm('Are you sure you want to delete this video?')) {
      this.videoService.deleteVideo(videoId).subscribe({
        next: () => {
          this.videos = this.videos.filter(v => v.id !== videoId);
        },
        error: (err) => {
          console.error('Error deleting video:', err);
          alert('Failed to delete video');
        }
      });
    }
  }
}