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
            // Parse markdown-style bold text (**text** -> <strong>text</strong>)
            let formattedExplanation = data.explanation.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            responseContent.innerHTML = formattedExplanation;
            aiResponseEl.style.display = 'block';
        } else {
            aiResponseEl.style.display = 'none';
        }

        if (data.results && data.results.length > 0) {
            searchResults.innerHTML = data.results.map((result, index) => {
                // Build keywords display with TF-IDF scores
                let keywordsHtml = '';
                if (result.keywords && result.keywords.length > 0) {
                    // Check if we have TF-IDF scores
                    if (result.tfidf_keywords && result.tfidf_keywords.length > 0) {
                        keywordsHtml = `
                            <div class="result-keywords">
                                <strong>🔑 Related Keywords (TF-IDF Ranked):</strong>
                                ${result.tfidf_keywords.map(tfidf => {
                            const score = tfidf[1];
                            const isHighScore = score > 0.05;
                            return `<span class="keyword-tag ${isHighScore ? 'high-tfidf' : ''}" title="TF-IDF: ${score.toFixed(4)}">${isHighScore ? '⭐ ' : ''}${tfidf[0]}</span>`;
                        }).join('')}
                            </div>
                        `;
                    } else {
                        keywordsHtml = `
                            <div class="result-keywords">
                                <strong>🔑 Related Keywords:</strong>
                                ${result.keywords.map(kw => `<span class="keyword-tag">${kw}</span>`).join('')}
                            </div>
                        `;
                    }
                }

                // Build contexts display
                let contextsHtml = '';
                if (result.contexts && result.contexts.length > 0) {
                    contextsHtml = `
                        <div class="result-contexts">
                            <strong>📝 Context Snippets:</strong>
                            ${result.contexts.slice(0, 2).map(ctx => `
                                <div class="context-snippet">
                                    <em>"${ctx.snippet}"</em>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }

                // Build summary display
                let summaryHtml = '';
                if (result.summary) {
                    // Split summary by newlines for better formatting
                    const summaryLines = result.summary.split('\n\n');
                    summaryHtml = `
                        <div class="result-summary">
                            ${summaryLines.map(line => `<p>${line}</p>`).join('')}
                        </div>
                    `;
                }

                return `
                    <div class="result-card ${result.relevance}">
                        <div class="result-header">
                            <div class="result-title">
                                <span class="result-rank">#${index + 1}</span>
                                ${result.name}
                            </div>
                            <div class="result-score">
                                <div class="score-badge">${result.score}%</div>
                            </div>
                        </div>
                        ${summaryHtml}
                        ${keywordsHtml}
                        ${contextsHtml}
                        <div class="result-meta">
                            <span>📊 ${result.occurrences || 0} occurrences</span>
                            <span class="relevance-badge ${result.relevance}">${result.relevance}</span>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            searchResults.innerHTML = '<div class="empty-state"><p>No results found</p></div>';
        }

        // Display aggregate summary if available
        this.displayAggregateSummary(data.aggregate_summary);
    }

    displayAggregateSummary(summary) {
        // Find or create aggregate summary container
        let summaryContainer = document.getElementById('aggregate-summary');

        if (!summary) {
            if (summaryContainer) {
                summaryContainer.style.display = 'none';
            }
            return;
        }

        // Create container if it doesn't exist
        if (!summaryContainer) {
            const resultsContainer = document.getElementById('results-container');
            summaryContainer = document.createElement('div');
            summaryContainer.id = 'aggregate-summary';
            summaryContainer.className = 'aggregate-summary';
            resultsContainer.appendChild(summaryContainer);
        }

        summaryContainer.style.display = 'block';

        // Build summary HTML
        const stats = summary.statistics;
        const keywords = summary.top_keywords || [];
        const themes = summary.themes || [];
        const topDocs = summary.top_documents || [];

        summaryContainer.innerHTML = `
            <div class="summary-header">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M9 5H7C6.46957 5 5.96086 5.21071 5.58579 5.58579C5.21071 5.96086 5 6.46957 5 7V19C5 19.5304 5.21071 20.0391 5.58579 20.4142C5.96086 20.7893 6.46957 21 7 21H17C17.5304 21 18.0391 20.7893 18.4142 20.4142C18.7893 20.0391 19 19.5304 19 19V7C19 6.46957 18.7893 5.96086 18.4142 5.58579C18.0391 5.21071 17.5304 5 17 5H15" stroke="currentColor" stroke-width="2"/>
                    <path d="M9 5C9 4.46957 9.21071 3.96086 9.58579 3.58579C9.96086 3.21071 10.4696 3 11 3H13C13.5304 3 14.0391 3.21071 14.4142 3.58579C14.7893 3.96086 15 4.46957 15 5V7C15 7.53043 14.7893 8.03914 14.4142 8.41421C14.0391 8.78929 13.5304 9 13 9H11C10.4696 9 9.96086 8.78929 9.58579 8.41421C9.21071 8.03914 9 7.53043 9 7V5Z" stroke="currentColor" stroke-width="2"/>
                </svg>
                <h3>📊 Search Summary</h3>
                <span class="summary-subtitle">Aggregate analysis across all results</span>
            </div>
            
            <div class="summary-grid">
                <div class="summary-stat-card">
                    <div class="stat-number">${stats.total_documents}</div>
                    <div class="stat-label">Documents</div>
                </div>
                <div class="summary-stat-card">
                    <div class="stat-number">${stats.total_occurrences}</div>
                    <div class="stat-label">Occurrences</div>
                </div>
                <div class="summary-stat-card">
                    <div class="stat-number">${stats.average_relevance}%</div>
                    <div class="stat-label">Avg Relevance</div>
                </div>
                <div class="summary-stat-card">
                    <div class="stat-number">${stats.high_relevance_docs}</div>
                    <div class="stat-label">High Relevance</div>
                </div>
            </div>
            
            <div class="summary-content">
                <div class="summary-narrative">
                    ${summary.narrative_summary.split('\n').map(line => {
            if (line.startsWith('**') && line.endsWith('**')) {
                return `<h4>${line.replace(/\*\*/g, '')}</h4>`;
            } else if (line.startsWith('•')) {
                return `<li>${line.substring(1).trim()}</li>`;
            } else if (line.trim()) {
                return `<p>${line}</p>`;
            }
            return '';
        }).join('')}
                </div>
                
                ${keywords.length > 0 ? `
                    <div class="summary-section">
                        <h4>🔑 Top Keywords Across All Documents</h4>
                        <div class="summary-keywords">
                            ${keywords.slice(0, 10).map(kw => `<span class="summary-keyword-tag">${kw}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
                
                ${themes.length > 0 ? `
                    <div class="summary-section">
                        <h4>💡 Recurring Themes</h4>
                        <div class="theme-tags">
                            ${themes.map(theme => `<span class="theme-tag">${theme}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
                
                ${topDocs.length > 0 ? `
                    <div class="summary-section">
                        <h4>📄 Top Matching Documents</h4>
                        <div class="top-docs-list">
                            ${topDocs.map((doc, idx) => `
                                <div class="top-doc-item">
                                    <span class="top-doc-rank">#${idx + 1}</span>
                                    <span class="top-doc-name">${doc.name}</span>
                                    <span class="top-doc-score">${doc.score}%</span>
                                    <span class="top-doc-occurrences">${doc.occurrences} matches</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
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
