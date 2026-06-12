
import { getAIConfig } from './storage.js';

class JobManager {
    constructor() {
        if (JobManager.instance) {
            return JobManager.instance;
        }

        this.subscribers = [];
        this.reset();
        JobManager.instance = this;
    }

    reset() {
        this.isGenerating = false;
        this.currentProgress = 0;
        this.currentStage = '';
        this.currentMessage = '';
        this.timeRemaining = '';
        this.currentJobType = '';
        this.result = null;
        this.error = null;
        // Do NOT clear subscribers here, as the UI stays subscribed across jobs
    }

    subscribe(callback) {
        this.subscribers.push(callback);
        // Immediately send current state
        callback(this.getState());
        return () => {
            this.subscribers = this.subscribers.filter(cb => cb !== callback);
        };
    }

    notify() {
        const state = this.getState();
        this.subscribers.forEach(cb => cb(state));
    }

    getState() {
        return {
            isGenerating: this.isGenerating,
            progress: this.currentProgress,
            stage: this.currentStage,
            message: this.currentMessage,
            timeRemaining: this.timeRemaining,
            jobType: this.currentJobType,
            result: this.result,
            error: this.error,
        };
    }

    async startJob(url, payload, options = {}) {
        if (this.isGenerating) {
            console.warn(`Job already running (${this.currentJobType || "unknown"})`);
            return;
        }

        const {
            initialProgress = 0,
            initialMessage = "Initializing connection...",
            initialTimeRemaining = "",
            jobType = "generic",
        } = options;

        this.reset(); // Clear old results
        this.isGenerating = true;
        this.currentProgress = initialProgress;
        this.currentMessage = initialMessage;
        this.timeRemaining = initialTimeRemaining;
        this.currentJobType = jobType;
        this.notify();

        try {
            const isFormData = payload instanceof FormData;
            const headers = isFormData ? {} : { 'Content-Type': 'application/json' };
            const aiConfig = getAIConfig();
            if (aiConfig.api_key) headers['X-Gemini-Api-Key'] = aiConfig.api_key;
            if (aiConfig.model) headers['X-Gemini-Model'] = aiConfig.model;
            const body = isFormData ? payload : JSON.stringify(payload);

            const response = await fetch(url, {
                method: 'POST',
                headers,
                body
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep partial line

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const event = JSON.parse(line);
                        this.handleEvent(event);
                    } catch (e) {
                        console.warn("JobManager JSON parse error:", e, line);
                    }
                }
            }

        } catch (err) {
            console.error("JobManager Error:", err);
            this.error = err.message;
            this.isGenerating = false;
            this.notify();
        }
    }

    handleEvent(event) {
        if (event.type === 'progress' || event.type === 'progress_start') {
            const nextProgress = Number(event.percent);
            if (Number.isFinite(nextProgress) && nextProgress < this.currentProgress) {
                // Keep progress monotonic to avoid jarring UI jumps at startup.
                return;
            }
            this.currentProgress = Number.isFinite(nextProgress) ? nextProgress : this.currentProgress;
            this.currentStage = event.stage || this.currentStage;
            this.currentMessage = event.message || this.currentMessage;
            if (event.time_remaining) {
                this.timeRemaining = event.time_remaining;
            }
        } else if (event.type === 'complete') {
            this.isGenerating = false;
            this.currentStage = 'complete';
            this.currentProgress = 100;
            this.currentMessage = 'Complete!';
            // Support both current and legacy payload shapes.
            this.result = event.result || event.data || event.business_growth_strategy || event.game_plan;
        } else if (event.type === 'error') {
            this.isGenerating = false;
            this.currentStage = 'error';
            this.error = event.message;
        }
        this.notify();
    }
}

export const jobManager = new JobManager();
