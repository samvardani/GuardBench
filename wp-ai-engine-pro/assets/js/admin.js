/**
 * Admin JavaScript
 */

(function($) {
    'use strict';
    
    // Content Generator
    $('#wpai-generate').on('click', async function() {
        const prompt = $('#wpai-prompt').val().trim();
        const $status = $('#wpai-status');
        
        if (!prompt) {
            alert('Please enter a prompt');
            return;
        }
        
        $status.removeClass('success error').addClass('loading').text('Generating content...').show();
        
        try {
            const response = await fetch(wpaiData.restUrl + 'generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-WP-Nonce': wpaiData.nonce
                },
                body: JSON.stringify({
                    prompt: prompt,
                    type: 'post'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Insert content into editor
                if (typeof wp !== 'undefined' && wp.data) {
                    // Gutenberg
                    wp.data.dispatch('core/editor').editPost({
                        content: data.content
                    });
                } else if (typeof tinymce !== 'undefined') {
                    // Classic editor
                    tinymce.activeEditor.setContent(data.content);
                }
                
                $status.removeClass('loading error').addClass('success').text('Content generated successfully!');
                $('#wpai-prompt').val('');
            } else {
                throw new Error(data.error || 'Generation failed');
            }
        } catch (error) {
            $status.removeClass('loading success').addClass('error').text('Error: ' + error.message);
        }
    });
    
})(jQuery);



