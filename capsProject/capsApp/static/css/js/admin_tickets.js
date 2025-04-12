
    // Get the modal
    const modal = document.getElementById('successModal');
    const closeModal = document.querySelector('.close-modal2');
    
    // Close modal when clicking X
    closeModal.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Handle form submissions
    const forms = document.querySelectorAll('.action-buttons');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch(window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success modal
                    const modal = document.getElementById('successModal');
                    modal.style.display = 'block';
                    
                    // Hide modal after 2 seconds
                    setTimeout(() => {
                        modal.style.display = 'none';
                        // Optionally refresh the page or update the status visually
                        location.reload();
                    }, 2000);
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });
