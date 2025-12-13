/**
 * video-recorder.js
 * Video recording functionality - captures visualization canvases + audio
 *
 * Composites all visualization canvases (waveform, spectrogram, axes, oscilloscope)
 * into a single video stream and combines with audio for download.
 */

import * as State from './audio-state.js';

// Recording state
let isRecording = false;
let mediaRecorder = null;
let recordedChunks = [];
let compositeCanvas = null;
let compositeCtx = null;
let rafId = null;
let recordingStartTime = null;

// Canvas references (cached for performance)
let waveformCanvas = null;
let waveformAxisCanvas = null;
let waveformXAxisCanvas = null;
let spectrogramCanvas = null;
let spectrogramAxisCanvas = null;
let oscilloscopeCanvas = null;

/**
 * Toggle video recording on/off
 */
export function toggleVideoRecording() {
    if (isRecording) {
        stopVideoRecording();
    } else {
        startVideoRecording();
    }
}

/**
 * Start video recording
 */
function startVideoRecording() {
    console.log('🎥 Starting video recording...');

    try {
        // Get canvas references
        waveformCanvas = document.getElementById('waveform');
        waveformAxisCanvas = document.getElementById('waveform-axis');
        waveformXAxisCanvas = document.getElementById('waveform-x-axis');
        spectrogramCanvas = document.getElementById('spectrogram');
        spectrogramAxisCanvas = document.getElementById('spectrogram-axis');
        oscilloscopeCanvas = document.getElementById('oscilloscope');

        if (!waveformCanvas || !spectrogramCanvas) {
            console.error('❌ Required canvases not found');
            alert('Error: Visualization canvases not ready');
            return;
        }

        // Check if audio recording destination exists
        if (!State.recordingDestination) {
            console.error('❌ Recording destination not initialized');
            alert('Error: Audio recording not set up. Please refresh the page.');
            return;
        }

        // Create composite canvas
        // Width: max of canvas widths + axis width
        // Height: sum of all canvas heights with padding
        const width = 1280;  // 1200 main + 60 axis + 20 padding
        const height = 720;  // Enough for all canvases vertically stacked

        compositeCanvas = document.createElement('canvas');
        compositeCanvas.width = width;
        compositeCanvas.height = height;
        compositeCtx = compositeCanvas.getContext('2d', {
            alpha: false,
            desynchronized: true  // Performance hint
        });

        // Start compositing loop at 30fps
        recordingStartTime = Date.now();
        compositeFrame();

        // Capture video stream from composite canvas
        const videoStream = compositeCanvas.captureStream(30);  // 30 fps

        // Get audio stream
        const audioStream = State.recordingDestination.stream;

        // Combine video + audio
        const combinedStream = new MediaStream([
            ...videoStream.getVideoTracks(),
            ...audioStream.getAudioTracks()
        ]);

        // Detect best supported format
        let mimeType;
        let extension;
        if (MediaRecorder.isTypeSupported('video/mp4')) {
            mimeType = 'video/mp4';
            extension = 'mp4';
            console.log('✅ Using MP4 format (PowerPoint compatible)');
        } else if (MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')) {
            mimeType = 'video/webm;codecs=vp9,opus';
            extension = 'webm';
            console.warn('⚠️ Using WebM format (not PowerPoint compatible)');
        } else {
            mimeType = 'video/webm';
            extension = 'webm';
            console.warn('⚠️ Using fallback WebM format');
        }

        // Create MediaRecorder
        recordedChunks = [];
        mediaRecorder = new MediaRecorder(combinedStream, {
            mimeType: mimeType,
            videoBitsPerSecond: 2500000,  // 2.5 Mbps for good quality
            audioBitsPerSecond: 128000    // 128 kbps for audio
        });

        // Handle data available
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        // Handle recording stop
        mediaRecorder.onstop = () => {
            console.log('🎬 Recording stopped, processing video...');

            // Create blob from chunks
            const blob = new Blob(recordedChunks, { type: mimeType });

            // Generate filename
            const filename = generateFilename(extension);

            // Download the video
            downloadVideo(blob, filename);

            // Cleanup
            cleanup();

            console.log(`✅ Video saved: ${filename} (${(blob.size / 1024 / 1024).toFixed(2)} MB)`);
        };

        // Handle errors
        mediaRecorder.onerror = (event) => {
            console.error('❌ MediaRecorder error:', event.error);
            alert('Recording error: ' + event.error);
            cleanup();
        };

        // Start recording
        mediaRecorder.start();
        isRecording = true;

        // Update button state
        updateButtonState(true);

        console.log(`🎥 Recording started (${mimeType})`);

    } catch (error) {
        console.error('❌ Error starting recording:', error);
        alert('Failed to start recording: ' + error.message);
        cleanup();
    }
}

/**
 * Stop video recording
 */
function stopVideoRecording() {
    console.log('⏹ Stopping video recording...');

    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        isRecording = false;
    }

    // Update button state immediately
    updateButtonState(false);
}

/**
 * Composite all canvases into one frame (called at 30fps via RAF)
 */
function compositeFrame() {
    if (!compositeCtx || !isRecording) {
        return;
    }

    // Clear canvas
    compositeCtx.fillStyle = '#1a1a1a';  // Dark background
    compositeCtx.fillRect(0, 0, compositeCanvas.width, compositeCanvas.height);

    // Layout parameters
    const padding = 10;
    let yOffset = padding;
    const xStart = padding;

    try {
        // Draw waveform section
        if (waveformCanvas) {
            compositeCtx.drawImage(waveformCanvas, xStart, yOffset);

            // Draw waveform Y-axis to the right
            if (waveformAxisCanvas) {
                compositeCtx.drawImage(waveformAxisCanvas, xStart + waveformCanvas.width, yOffset);
            }

            yOffset += waveformCanvas.height;

            // Draw waveform X-axis below
            if (waveformXAxisCanvas) {
                compositeCtx.drawImage(waveformXAxisCanvas, xStart, yOffset);
                yOffset += waveformXAxisCanvas.height;
            }
        }

        yOffset += padding;  // Space between sections

        // Draw spectrogram section
        if (spectrogramCanvas) {
            compositeCtx.drawImage(spectrogramCanvas, xStart, yOffset);

            // Draw spectrogram Y-axis to the right
            if (spectrogramAxisCanvas) {
                compositeCtx.drawImage(spectrogramAxisCanvas, xStart + spectrogramCanvas.width, yOffset);
            }

            yOffset += spectrogramCanvas.height;
        }

        yOffset += padding;

        // Draw oscilloscope (bottom right corner)
        if (oscilloscopeCanvas) {
            const oscX = compositeCanvas.width - oscilloscopeCanvas.width - padding;
            const oscY = compositeCanvas.height - oscilloscopeCanvas.height - padding;
            compositeCtx.drawImage(oscilloscopeCanvas, oscX, oscY);
        }

        // Optional: Add text overlay (volcano name, timestamp)
        const volcanoSelect = document.getElementById('volcano');
        const volcanoName = volcanoSelect ? volcanoSelect.options[volcanoSelect.selectedIndex]?.text : '';

        if (volcanoName) {
            compositeCtx.fillStyle = 'rgba(255, 255, 255, 0.9)';
            compositeCtx.font = 'bold 16px Arial';
            compositeCtx.fillText(volcanoName, xStart, 25);
        }

        // Recording indicator (red dot)
        const elapsed = ((Date.now() - recordingStartTime) / 1000).toFixed(0);
        compositeCtx.fillStyle = '#ff0000';
        compositeCtx.beginPath();
        compositeCtx.arc(compositeCanvas.width - 50, 20, 8, 0, Math.PI * 2);
        compositeCtx.fill();

        compositeCtx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        compositeCtx.font = '14px Arial';
        compositeCtx.fillText(`${elapsed}s`, compositeCanvas.width - 35, 25);

    } catch (error) {
        console.error('❌ Error compositing frame:', error);
    }

    // Schedule next frame
    if (isRecording) {
        rafId = requestAnimationFrame(compositeFrame);
    }
}

/**
 * Generate filename following the same pattern as audio download
 */
function generateFilename(extension) {
    const volcanoSelect = document.getElementById('volcano');
    const volcano = volcanoSelect ? volcanoSelect.value : 'Unknown';

    const volcanoName = volcano.charAt(0).toUpperCase() + volcano.slice(1);

    const metadata = State.currentMetadata;
    const station = metadata?.station || 'Unknown';
    const channel = metadata?.channel || 'Z';

    // Calculate duration in hours
    const durationHours = Math.round(State.totalAudioDuration / 3600);

    // Get data end time for filename
    const endTime = State.dataEndTime || new Date();
    const year = endTime.getUTCFullYear();
    const month = String(endTime.getUTCMonth() + 1).padStart(2, '0');
    const day = String(endTime.getUTCDate()).padStart(2, '0');
    const hour = String(endTime.getUTCHours()).padStart(2, '0');
    const minute = String(endTime.getUTCMinutes()).padStart(2, '0');

    return `${volcanoName}_${station}_${channel}_Last_${durationHours}_Hrs_From_${year}_${month}_${day}_${hour}_${minute}.${extension}`;
}

/**
 * Download the video file
 */
function downloadVideo(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();

    // Cleanup
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 100);
}

/**
 * Update button state
 */
function updateButtonState(recording) {
    const btn = document.getElementById('recordVideoBtn');
    if (!btn) return;

    if (recording) {
        btn.textContent = '⏹ Stop Recording';
        btn.style.background = '#7c2f2f';  // Red
        btn.style.color = '#f8f1f1';
        btn.style.borderColor = '#8c3f3f';
    } else {
        btn.textContent = '🎥 Record Video';
        btn.style.background = '#2f5a7c';  // Blue
        btn.style.color = '#f1f6f8';
        btn.style.borderColor = '#3f6a8c';
    }
}

/**
 * Cleanup resources
 */
function cleanup() {
    // Cancel RAF loop
    if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
    }

    // Clear recording state
    isRecording = false;
    mediaRecorder = null;
    recordedChunks = [];
    compositeCanvas = null;
    compositeCtx = null;
    recordingStartTime = null;

    // Clear canvas references
    waveformCanvas = null;
    waveformAxisCanvas = null;
    waveformXAxisCanvas = null;
    spectrogramCanvas = null;
    spectrogramAxisCanvas = null;
    oscilloscopeCanvas = null;

    // Update button state
    updateButtonState(false);
}
