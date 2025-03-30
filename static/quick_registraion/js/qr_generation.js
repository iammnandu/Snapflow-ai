/**
 * Quick Registration JavaScript Functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Copy registration link to clipboard
    const copyLinkButtons = document.querySelectorAll('.copy-link');
    if (copyLinkButtons.length > 0) {
        copyLinkButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const link = this.getAttribute('data-link');
                
                // Create a temporary input element
                const tempInput = document.createElement('input');
                tempInput.value = link;
                document.body.appendChild(tempInput);
                tempInput.select();
                document.execCommand('copy');
                document.body.removeChild(tempInput);
                
                // Show success message
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check"></i> Copied!';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        });
    }
    
    // Profile image preview
    const profileImageInput = document.getElementById('id_profile_image');
    if (profileImageInput) {
        profileImageInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    // Check if preview element exists, otherwise create it
                    let previewContainer = document.getElementById('profile-preview-container');
                    if (!previewContainer) {
                        previewContainer = document.createElement('div');
                        previewContainer.id = 'profile-preview-container';
                        previewContainer.className = 'mt-2 text-center';
                        profileImageInput.parentNode.appendChild(previewContainer);
                    }
                    
                    previewContainer.innerHTML = `
                        <div class="mb-2">Preview:</div>
                        <img src="${e.target.result}" alt="Profile Preview" class="img-thumbnail" style="max-height: 150px;">
                    `;
                }
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
    
    // Registration form validation
    const registrationForm = document.querySelector('.needs-validation');
    if (registrationForm) {
        registrationForm.addEventListener('submit', function(event) {
            if (!registrationForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            registrationForm.classList.add('was-validated');
        });
    }
});