class ContactExtractor {
    constructor() {
        this.urlInput = document.getElementById('profileUrl');
        this.fetchBtn = document.getElementById('fetchBtn');
        this.resultsSection = document.getElementById('resultsSection');
        this.loadingIndicator = document.getElementById('loadingIndicator');

        this.setupEventListeners();
        this.setupSampleButtons();

        // Auto-load on page load
        window.addEventListener('load', () => {
            this.fetchContacts();
        });
    }

    setupEventListeners() {
        this.fetchBtn.addEventListener('click', () => this.fetchContacts());

        this.urlInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.fetchContacts();
            }
        });
    }

    setupSampleButtons() {
        document.querySelectorAll('.sample-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const url = btn.dataset.url;
                if (url) {
                    this.urlInput.value = url;
                    this.fetchContacts();
                }
            });
        });
    }

    async fetchContacts() {
        let url = this.urlInput.value.trim();

        if (!url) {
            this.showError('Please enter a valid URL');
            return;
        }

        // Add protocol if missing
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
            this.urlInput.value = url;
        }

        // Show loading
        this.showLoading(true);
        this.clearResults();

        try {
            const response = await fetch('/api/extract', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to extract contacts');
            }

            if (data.success) {
                this.displayResults(data);
            } else {
                throw new Error(data.error || 'Failed to extract contacts');
            }

        } catch (error) {
            console.error('Error:', error);
            this.showError(error.message || 'Something went wrong. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }

    displayResults(data) {
        const { data: contacts, platform, url, timestamp } = data;

        const platformIcons = {
            linkedin: 'fab fa-linkedin',
            instagram: 'fab fa-instagram',
            facebook: 'fab fa-facebook',
            twitter: 'fab fa-twitter',
            youtube: 'fab fa-youtube',
            generic: 'fas fa-globe'
        };

        const iconClass = platformIcons[platform] || platformIcons.generic;
        const platformName = platform.charAt(0).toUpperCase() + platform.slice(1);

        // Check if all values are "Not found"
        const allNotFound = contacts.phone === 'Not found' &&
            contacts.email === 'Not found' &&
            contacts.office === 'Not found';

        let html = `
            <div class="contact-result">
                <div class="contact-header">
                    <div class="contact-platform">
                        <i class="${iconClass}"></i>
                        <span>${platformName}</span>
                        <span class="badge">${allNotFound ? 'No Data Found' : 'Extracted'}</span>
                    </div>
                    <div class="contact-url" title="${url}">
                        ${this.truncateUrl(url)}
                    </div>
                </div>
                
                <div class="contact-items">
                    ${this.createContactItem('fas fa-phone-alt', 'Phone', contacts.phone || 'Not found')}
                    ${this.createContactItem('fas fa-envelope', 'Email', contacts.email || 'Not found')}
                    ${this.createContactItem('fas fa-map-pin', 'Office Address', contacts.office || 'Not found')}
                </div>
                
                <div class="contact-timestamp">
                    <i class="far fa-clock"></i> Fetched: ${new Date(timestamp).toLocaleString()}
                </div>
            </div>
        `;

        this.resultsSection.innerHTML = html;
        this.resultsSection.style.display = 'block';
    }

    createContactItem(iconClass, label, value) {
        const isNotFound = value === 'Not found' || value === 'Not found on public profile';
        const valueClass = isNotFound ? 'not-found' : '';

        // Check if value contains numbered addresses (1., 2., 3.)
        let displayValue = value;
        if (value && value.includes('\n\n') && !isNotFound) {
            // Format with proper HTML for better display
            const addressItems = value.split('\n\n').filter(addr => addr.trim());
            displayValue = addressItems.map(addr => {
                // Check if it starts with a number (1., 2., etc.)
                if (addr.match(/^\d+\./)) {
                    return `<span class="address-item">${addr}</span>`;
                }
                return `<span class="address-item">${addr}</span>`;
            }).join('');
        }

        return `
        <div class="contact-item">
            <div class="contact-icon">
                <i class="${iconClass}"></i>
            </div>
            <div class="contact-info">
                <div class="contact-label">${label}</div>
                <div class="contact-value ${valueClass}">${displayValue}</div>
            </div>
        </div>
    `;
    }

    truncateUrl(url) {
        const maxLength = 40;
        if (url.length <= maxLength) return url;
        return url.substring(0, maxLength) + '...';
    }

    showLoading(show) {
        this.loadingIndicator.style.display = show ? 'flex' : 'none';
        this.fetchBtn.disabled = show;
        if (show) {
            this.fetchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Extracting...';
        } else {
            this.fetchBtn.innerHTML = '<i class="fas fa-search"></i> Fetch';
        }
    }

    showError(message) {
        this.resultsSection.innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-circle"></i>
                <p>${message}</p>
            </div>
        `;
        this.resultsSection.style.display = 'block';
    }

    clearResults() {
        this.resultsSection.innerHTML = '';
    }
}

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    new ContactExtractor();
});
