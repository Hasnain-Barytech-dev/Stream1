// frontend-test-client/src/app/components/upload/upload.component.ts
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { UploadService } from '../../services/upload.service';
import { VideoUploadProgress } from '../../models/video.model';
import { finalize, forkJoin, Observable } from 'rxjs';

@Component({
  selector: 'app-upload',
  templateUrl: './upload.component.html',
  styleUrls: ['./upload.component.scss']
})
export class UploadComponent implements OnInit {
  uploadForm: FormGroup;
  selectedFile: File | null = null;
  uploadInProgress = false;
  uploadProgress = 0;
  currentVideoId: string | null = null;
  uploadError: string | null = null;
  
  constructor(
    private fb: FormBuilder,
    private uploadService: UploadService
  ) {
    this.uploadForm = this.fb.group({
      title: ['', Validators.required],
      description: ['']
    });
  }

  ngOnInit(): void {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length) {
      this.selectedFile = input.files[0];
    }
  }

  async onSubmit(): Promise<void> {
    if (!this.uploadForm.valid || !this.selectedFile) {
      return;
    }

    this.uploadInProgress = true;
    this.uploadError = null;
    
    try {
      // Initialize upload
      const initialization = await this.uploadService.initializeUpload(
        this.selectedFile.name,
        this.selectedFile.size,
        this.selectedFile.type,
        this.uploadForm.value.title,
        this.uploadForm.value.description
      ).toPromise();
      
      if (!initialization) {
        throw new Error('Failed to initialize upload');
      }
      
      this.currentVideoId = initialization.video_id;
      
      // Split file into chunks and upload
      const chunkSize = 5 * 1024 * 1024; // 5MB chunks
      const chunks = this.uploadService.createChunks(this.selectedFile, chunkSize);
      const totalChunks = chunks.length;
      
      // Upload each chunk in sequence
      for (let i = 0; i < chunks.length; i++) {
        const chunkBlob = chunks[i];
        const chunkFile = new File([chunkBlob], this.selectedFile.name);
        
        await this.uploadService.uploadChunk(
          chunkFile, 
          initialization.video_id, 
          i, 
          totalChunks
        ).toPromise();
        
        this.uploadProgress = Math.round(((i + 1) / totalChunks) * 100);
      }
      
      // Reset form after successful upload
      this.uploadForm.reset();
      this.selectedFile = null;
      this.uploadInProgress = false;
      
    } catch (error) {
      console.error('Upload error:', error);
      this.uploadError = 'Failed to upload video';
      this.uploadInProgress = false;
    }
  }

  cancelUpload(): void {
    if (this.currentVideoId) {
      this.uploadService.cancelUpload(this.currentVideoId).subscribe(() => {
        this.resetUpload();
      });
    } else {
      this.resetUpload();
    }
  }

  private resetUpload(): void {
    this.uploadInProgress = false;
    this.uploadProgress = 0;
    this.currentVideoId = null;
    this.uploadError = null;
  }
}