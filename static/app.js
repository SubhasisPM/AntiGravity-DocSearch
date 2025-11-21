// DocSearch - Frontend JavaScript for Flask App

class DocSearchApp {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadDocuments();
    }

    setupEventListeners() {
        document.getElementById('upload-btn').addEventListener('click', () => {
            document.getElementById('file-input').click();
        });

        document.getElementById('file-input').addEventListener('change', (e) => {
            this.handleFileUpload(e.target.files);
        });

        document.getElementById('search-btn').addEventListener('click', () => {
            this.performSearch();
        });

        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
    }

    async handleFileUpload(files) {
        if (files.length === 0) return;

        const fileList = document.getElementById('file-list');
        fileList.innerHTML = '';

        for (let file of files) {
            await this.uploadFile(file);
        }

        this.loadDocuments();
    }

    async uploadFile(file) {
        const fileList = document.getElementById('file-list');

        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <svg class="file-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" stroke="currentColor" stroke-width="2"/>
                    <path d="M13 2V9H20" stroke="currentColor" stroke-width="2"/>
                </svg>
                <div>
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${this.formatFileSize(file.size)}</div>
                </div>
            </div>
            <span class="file-status processing">Processing</span>
        `;
        fileList.appendChild(fileItem);

        const formData = new FormData();
        formData.append('file', file);

        try {
            this.showLoading(true);
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                const statusEl = fileItem.querySelector('.file-status');
                statusEl.textContent = 'Ready';
                statusEl.className = 'file-status ready';
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            const statusEl = fileItem.querySelector('.file-status');
            statusEl.textContent = 'Error';
            statusEl.className = 'file-status error';
        } finally {
            this.showLoading(false);
        }
    }

    async performSearch() {
        const query = document.getElementById('search-input').value.trim();
        if (!query) return;

        try {
            this.showLoading(true);

            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: query })
            });

            const data = await response.json();

            if (data.error) {
                this.showNoResults(data.error);
            } else {
                this.displayResults(data);
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showNoResults('An error occurred during search');
        } finally {
            this.showLoading(false);
        }
    }

    displayResults(data) {
        const aiResponseEl = document.getElementById('ai-response');
        const responseContent = document.getElementById('response-content');
        const searchResults = document.getElementById('search-results');

        if (data.explanation) {
            responseContent.textContent = data.explanation;
            aiResponseEl.style.display = 'block';
        } else {
            aiResponseEl.style.display = 'none';
        }

        if (data.results && data.results.length > 0) {
            searchResults.innerHTML = data.results.map((result, index) => `
                <div class="result-card">
                    <div class="result-header">
                        <div class="result-title">
                            <span class="result-rank">#${index + 1}</span>
                            ${result.name}
                        </div>
                        <div class="result-score">
                            ${result.score} Matches
                        </div>
                    </div>
                    <div class="result-content">
                        Found ${result.score} occurrences of your search terms in this document.
                    </div>
                    <div class="result-meta">
                        <span>📊 Total Words: ${result.total_words}</span>
                    </div>
                </div>
            `).join('');
        } else {
            searchResults.innerHTML = '<div class="empty-state"><p>No results found</p></div>';
        }
    }

    showNoResults(message) {
        const aiResponseEl = document.getElementById('ai-response');
        const searchResults = document.getElementById('search-results');

        aiResponseEl.style.display = 'none';
        searchResults.innerHTML = `
            <div class="empty-state">
                <p>${message}</p>
            </div>
        `;
    }

    async loadDocuments() {
        try {
            const response = await fetch('/documents');
            const data = await response.json();

            document.getElementById('doc-count').textContent = data.documents.length;
            this.renderDocuments(data.documents);
        } catch (error) {
            console.error('Error loading documents:', error);
        }
    }

    renderDocuments(documents) {
        const documentsGrid = document.getElementById('documents-grid');

        if (documents.length === 0) {
            documentsGrid.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" stroke="currentColor" stroke-width="2"/>
                        <path d="M13 2V9H20" stroke="currentColor" stroke-width="2"/>
                    </svg>
                    <p>No documents yet. Upload some to get started!</p>
                </div>
            `;
            return;
        }

        documentsGrid.innerHTML = documents.map(doc => `
            <div class="document-card">
                <svg class="document-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" stroke="currentColor" stroke-width="2"/>
                    <path d="M13 2V9H20" stroke="currentColor" stroke-width="2"/>
                </svg>
                <div class="document-title">${doc.name}</div>
                <div class="document-meta">
                    <span>${this.formatFileSize(doc.size)}</span>
                </div>
            </div>
        `).join('');
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new DocSearchApp();
});
