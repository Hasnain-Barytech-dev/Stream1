// frontend-test-client/src/app/components/video-player/video-player.component.ts
import { Component, OnInit, Input, ElementRef, ViewChild, OnDestroy } from '@angular/core';
import { VideoService } from '../../services/video.service';
import { Video, StreamingManifest } from '../../models/video.model';
import * as Hls from 'hls.js';
import * as dashjs from 'dashjs';

@Component({
  selector: 'app-video-player',
  templateUrl: './video-player.component.html',
  styleUrls: ['./video-player.component.scss']
})
export class VideoPlayerComponent implements OnInit, OnDestroy {
  @Input() videoId: string;
  @ViewChild('videoPlayer') videoElement: ElementRef<HTMLVideoElement>;
  
  video: Video | null = null;
  loading = true;
  error: string | null = null;
  
  private hls: Hls | null = null;
  private dashPlayer: dashjs.MediaPlayerClass | null = null;

  constructor(private videoService: VideoService) { }

  ngOnInit(): void {
    this.loadVideo();
  }

  ngOnDestroy(): void {
    this.destroyPlayer();
  }

  private loadVideo(): void {
    this.loading = true;
    this.error = null;
    
    this.videoService.getVideoMetadata(this.videoId).subscribe({
      next: (video) => {
        this.video = video;
        if (video.status === 'ready') {
          this.setupPlayer();
        } else {
          this.error = `Video is not ready for playback (Status: ${video.status})`;
          this.loading = false;
        }
      },
      error: (err) => {
        console.error('Error loading video:', err);
        this.error = 'Failed to load video';
        this.loading = false;
      }
    });
  }

  private setupPlayer(): void {
    // Default to HLS, but check if browser supports it
    this.videoService.getStreamingManifest(this.videoId, 'hls').subscribe({
      next: (manifest) => {
        const video = this.videoElement.nativeElement;
        
        if (Hls.isSupported()) {
          this.setupHlsPlayer(manifest.manifest_url, video);
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
          // Native HLS support (Safari)
          video.src = manifest.manifest_url;
          video.addEventListener('loadedmetadata', () => {
            this.loading = false;
          });
        } else {
          // Fallback to DASH
          this.fallbackToDash();
        }
      },
      error: () => {
        this.fallbackToDash();
      }
    });
  }

  private setupHlsPlayer(manifestUrl: string, videoElement: HTMLVideoElement): void {
    this.destroyPlayer();
    
    this.hls = new Hls();
    this.hls.loadSource(manifestUrl);
    this.hls.attachMedia(videoElement);
    
    this.hls.on(Hls.Events.MANIFEST_PARSED, () => {
      this.loading = false;
      videoElement.play().catch(err => console.error('Playback error:', err));
    });
    
    this.hls.on(Hls.Events.ERROR, (event, data) => {
      if (data.fatal) {
        switch(data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            console.error('Fatal network error', data);
            this.hls?.startLoad();
            break;
          case Hls.ErrorTypes.MEDIA_ERROR:
            console.error('Fatal media error', data);
            this.hls?.recoverMediaError();
            break;
          default:
            this.destroyPlayer();
            this.error = 'Failed to play video';
            break;
        }
      }
    });
  }

  private fallbackToDash(): void {
    this.videoService.getStreamingManifest(this.videoId, 'dash').subscribe({
      next: (manifest) => {
        const video = this.videoElement.nativeElement;
        
        this.destroyPlayer();
        this.dashPlayer = dashjs.MediaPlayer().create();
        this.dashPlayer.initialize(video, manifest.manifest_url, true);
        this.dashPlayer.on('error', (e) => {
          console.error('DASH player error:', e);
          this.error = 'Video playback error';
        });
        
        this.loading = false;
      },
      error: (err) => {
        console.error('Error getting DASH manifest:', err);
        this.error = 'Failed to load video';
        this.loading = false;
      }
    });
  }

  private destroyPlayer(): void {
    if (this.hls) {
      this.hls.destroy();
      this.hls = null;
    }
    
    if (this.dashPlayer) {
      this.dashPlayer.reset();
      this.dashPlayer = null;
    }
  }
}