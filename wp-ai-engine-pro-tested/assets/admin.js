/**
 * Admin JavaScript
 * 
 * @package WPAIEnginePro
 */

(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Copy to clipboard functionality
        $('.wpai-copy-btn').on('click', function() {
            const text = $(this).data('copy');
            
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(function() {
                    alert('Copied to clipboard!');
                }).catch(function(err) {
                    console.error('Failed to copy:', err);
                });
            } else {
                // Fallback for older browsers
                const $temp = $('<textarea>');
                $('body').append($temp);
                $temp.val(text).select();
                document.execCommand('copy');
                $temp.remove();
                alert('Copied to clipboard!');
            }
        });
        
        // Show/hide API key toggle
        $('#wpai_show_api_key').on('change', function() {
            const $apiKeyInput = $('#wpai_api_key');
            $apiKeyInput.attr('type', this.checked ? 'text' : 'password');
        });
    });
    
})(jQuery);

