// Tab switching functionality
document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.nav-tab');
    const sections = document.querySelectorAll('.section');

    tabs.forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault(); // Prevent the default anchor behavior
            
            // Remove active class from all tabs and sections
            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Show corresponding section
            const sectionId = this.getAttribute('data-section');
            const targetSection = document.getElementById(sectionId);
            if (targetSection) {
                targetSection.classList.add('active');
            }

            // Update URL hash without scrolling
            history.pushState(null, '', `#${sectionId}`);
        });
    });

    // Handle initial load with hash
    const hash = window.location.hash.substring(1);
    if (hash) {
        const activeTab = document.querySelector(`.nav-tab[data-section="${hash}"]`);
        if (activeTab) {
            activeTab.click();
        }
    }
});

// Handle browser back/forward buttons
window.addEventListener('popstate', function() {
    const hash = window.location.hash.substring(1) || 'chat'; // Default to chat if no hash
    const activeTab = document.querySelector(`.nav-tab[data-section="${hash}"]`);
    if (activeTab) {
        activeTab.click();
    }
}); 