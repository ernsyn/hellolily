(function ($, window, document, undefined) {
    var editor;

    window.HLInbox = {
        config: {
            accountDeactivatedMessage: 'Your account doesn\'t seem to be active. Please activate your account to view your email.',
            inboxCcInput: '.inbox-compose .mail-to .inbox-cc',
            inboxBccInput: '.inbox-compose .mail-to .inbox-bcc',
            singleMessageSelector: '.inbox-content .view-message',
            templateField: '#id_template',
            inboxComposeSubmit: '.inbox-compose [type="submit"]',
            wysiHtmlToolbar: '#wysihtml5-toolbar',
            replyButton: '.reply-btn',
            tagsAjaxSelector: '.tags-ajax',
            emailAccountInput: '#id_send_from',
            sendToNormalField: '#id_send_to_normal',
            overwriteTemplateConfirm: 'Selecting a different template will overwrite the text you\'ve typed. Do you want to load the template anyway?',
            emptyTemplateAttachmentRow: '#empty-template-attachment-row',
            templateAttachmentDeleteButton: '#template-attachments [data-formset-delete-button]',
            templateAttachmentUndoDeleteButton: '#template-attachments [data-formset-undo-delete]',
            templateAttachmentsDiv: '#template-attachments',
            templateAttachmentName: '.template-attachment-name',
            templateAttachmentIds: '#template-attachment-ids',
            templateAttachmentId: '.template-attachment-id',
            templateAttachmentRow: '.template-attachment-row',
            currentTemplate: null,
            previousSendToNormalLength: 0
        },

        init: function (config) {
            var self = this;

            // Setup config
            if (typeof (config === 'object')) {
                $.extend(this.config, config);
            }

            self.initListeners();
            Metronic.initUniform();
        },

        initListeners: function() {
            var self = this,
                cf = self.config;

            $('body')
                .on('click', cf.inboxCcInput, function() {
                    // Handle compose/reply cc input toggle
                    self.handleAdditionalRecipientsInput('cc');
                })
                .on('click', cf.inboxBccInput, function() {
                    // Handle compose/reply bcc input toggle
                    self.handleAdditionalRecipientsInput('bcc');
                })
                .on('change', cf.emailAccountInput, function () {
                    self.changeTemplateField.call(self, cf.templateField, false);
                })
                .on('change', cf.templateField, function () {
                    self.changeTemplateField.call(self, this, true);
                })
                .on('change', cf.sendToNormalField, function () {
                    var previousSendToNormalLength = self.config.previousSendToNormalLength;

                    var inputLength = $(this).select2('data').length;
                    self.config.previousSendToNormalLength = inputLength;

                    // Don't do anything if it's just an extra recipient being added/removed
                    // or the last recipient is removed
                    if (inputLength > 1 || inputLength < previousSendToNormalLength) {
                        return false;
                    }

                    self.changeTemplateField.call(self, cf.templateField, false);
                })
                .on('click', cf.replyButton, function () {
                    // Open links when clicking the reply button
                    $('.inbox-view').hide();
                    $('.inbox-loading').show();
                })
                .on('click', cf.inboxComposeSubmit, function (event) {
                    self.handleInboxComposeSubmit(this, event);
                })
                .on('change', cf.tags, function () {
                    self.handleTagsAjaxChange(this);
                })
                .on('click', cf.templateAttachmentDeleteButton, function () {
                    var attachmentRow = $(this).closest('.form-group');
                    self.handleTemplateAttachmentsChange(attachmentRow);
                })
                .on('click', cf.templateAttachmentUndoDeleteButton, function () {
                    var attachmentRow = $(this).closest('.form-group');
                    self.handleTemplateAttachmentsChange(attachmentRow);
                });

                $('.inbox-compose input').on('keydown keyup keypress', function(event) {
                    // Make sure pressing enter doesn't do anything (except selecting something in a dropdown)
                    if (event.which == 13) {
                        event.preventDefault();
                    }
                });
        },

        customParser: function () {
            function parse(elementOrHtml, rules, context, cleanUp) {
                return elementOrHtml;
            }

            return parse;
        },

        initEmailCompose: function (emailComposeConfig) {
            var self = this;

            if (typeof (emailComposeConfig === 'object')) {
                $.extend(self.config, emailComposeConfig);
            }

            self.initWysihtml5();

            // If loadDefaultTemplate isn't set there was an error, so don't do any template loading
            if (self.config.loadDefaultTemplate !== null) {
                if (self.config.loadDefaultTemplate) {
                    // If no template was given in the url, load the default template
                    self.loadDefaultEmailTemplate();
                }
                else {
                    // Otherwise trigger change event so the given template gets loaded
                    $(self.config.templateField).val(self.config.template).change();
                }
            }

            if (self.config.recipient) {
                $(self.config.sendToNormalField).select2('data', self.config.recipient);
            }

            // Decode special chars
            var decodedEditorValue = self.decodeEntities(editor.getValue());
            var $composeEmailTemplate = $(decodedEditorValue).closest('#compose-email-template');

            // If there's a template, we're dealing with a draft, so set currentTemplate
            if ($composeEmailTemplate.length) {
                self.config.currentTemplate = $composeEmailTemplate[0].innerHTML;
            }
        },

        // Courtesy of Robert K/Ian Clark @ http://stackoverflow.com/questions/5796718/html-entity-decode/9609450#9609450
        decodeEntities: function (str) {
            // This prevents any overhead from creating the object each time
            var element = document.createElement('div');

            if (str && typeof str === 'string') {
                // Strip script/html tags
                str = str.replace(/<script[^>]*>([\S\s]*?)<\/script>/gmi, '');
                str = str.replace(/<\/?\w(?:[^"'>]|"[^"]*"|'[^']*')*>/gmi, '');
                element.innerHTML = str;
                str = element.textContent;
                element.textContent = '';
            }

            return str;
        },

        initWysihtml5: function () {
            var self = this;

            editor = new wysihtml5.Editor('id_body_html', {
                toolbar: 'wysihtml5-toolbar',
                parser: self.customParser(),
                handleTables: false
            });

            editor.observe('load', function () {
                // Initial value is most likely reply/forward text, so store it for later usage
                self.config.initialEditorValue = editor.getValue();
                // Extra div is needed so the editor auto resizes
                editor.setValue(self.config.initialEditorValue + '<div id="resize-div"></div>');

                $(this.composer.element).on('keydown paste change focus blur', function () {
                    self.resizeEditor();
                });

                // Make the editor the correct height on load
                self.resizeEditor();
            });

            // Set heading properly after change
            var toolbar = $(self.config.wysiHtmlToolbar);
            $(toolbar).find('a[data-wysihtml5-command="formatBlock"]').click(function(e) {
                var target = e.target || e.srcElement;
                var el = $(target);
                $(toolbar).find('.current-font').text(el.html());
            });

            // Not putting this in the initListeners since it's only used in the email compose
            $(window).on('resize', function() {
                self.resizeEditor();
            });
        },

        resizeEditor: function () {
            $('.wysihtml5-sandbox')[0].style.height = editor.composer.element.scrollHeight + 'px';
        },

        handleAdditionalRecipientsInput: function (inputType) {
            var $ccLink = $('.inbox-compose .mail-to .inbox-' + inputType);
            var $inputField = $('.inbox-compose .input-' + inputType);
            $ccLink.hide();
            $inputField.show();
            $('.close', $inputField).click(function () {
                $inputField.hide();
                $ccLink.show();
                $inputField.find('.tags').select2('val', '');
            });
        },

        changeTemplateField: function (templateField, templateChanged) {
            var self = this;
            if (self.config.templateList) {
                var selectedTemplate = parseInt($(templateField).val());
                var recipientId = null;
                var emailAccountId = $(self.config.emailAccountInput).val();

                if (emailAccountId) {
                    if (selectedTemplate) {
                        var recipient = $('#id_send_to_normal').select2('data')[0];

                        if (typeof recipient !== 'undefined' && typeof recipient.object_id !== 'undefined') {
                            // Check if a contact has been entered
                            recipientId = recipient.object_id;
                        }
                        else if (self.config.sender !== '' && self.config.sender != null) {
                            // If it's a reply there might be contact set
                            recipientId = self.config.sender;
                            self.config.sender = null;
                        }

                        // Always get a template
                        var url = self.config.getTemplateUrl + selectedTemplate + '/';

                        if (recipientId != null) {
                            // If a recipient has been set we can set extra url parameters
                            url += '?contact_id=' + recipientId + '&emailaccount_id=' + emailAccountId;
                        }
                        else {
                            url += '?emailaccount_id=' + emailAccountId;
                        }

                        $.getJSON(url, function (data) {
                            self.setNewEditorValue(data, templateChanged);
                        });
                    }
                }
                else {
                    toastr.error('I couldn\'t load the template because your email account doesn\'t seem to be set. Please check your email account and try again');
                }
            }
        },

        handleInboxComposeSubmit: function (inboxCompose, event) {
            event.preventDefault();

            var buttonName = $(inboxCompose).attr('name'),
                $form = $($(inboxCompose).closest('form'));

            if (buttonName == 'submit-discard') {
                // Discarding email, remove all attachments to prevent unneeded uploading.
                //$('[id|=id_attachments]:file').remove();
                // Prevent discard from submitting form. This will probably be made nicer later (LILY-787)
                window.location = '/#/email/all/INBOX';
                return;
            } else if (buttonName == 'submit-send') {
                // Validation of fields.
                if (!$('#id_send_to_normal').val() && !$('#id_send_to_cc').val() && !$('#id_send_to_bcc').val()) {
                    $('#modal_no_email_address').modal();
                    event.preventDefault();
                    return;
                }
            } else if (buttonName == 'submit-save') {
                var draftPk = $('#id_draft_pk').val();
                // If we are saving a (existing) draft, change url
                if(draftPk) {
                    $form.attr('action', '/messaging/email/draft/' + draftPk + '/');
                } else {
                    $form.attr('action', '/messaging/email/draft/');
                }
            }
            else if (buttonName == 'submit-send-archive') {
                // Send and archive was pressed, so set an extra field
                $('<input />').attr('type', 'hidden')
                    .attr('name', 'archive')
                    .attr('value', true)
                    .appendTo($form);
            }
            else {
                // No valid button, so do nothing;
                return;
            }

            // Remove unnecessary html
            var $containerDiv = $('<div id="email-container-div">');
            $containerDiv[0].innerHTML = HLInbox.getEditor().getValue();

            var templateContent = '';
            // Get template content if we're not dealing with the creation of a draft and there is a template set
            if (buttonName != 'submit-save' && $containerDiv.find('#compose-email-template').length) {
                templateContent = $containerDiv.find('#compose-email-template')[0].innerHTML;

                // Remove email template div and resize div and only keep user typed text
                $containerDiv.find('#compose-email-template').remove();
            }

            $containerDiv.find('#resize-div').remove();

            /**
             * You'd expect HLInbox.getEditor().setValue or $('#id_body_html').html
             * would work to set the value of the textarea.
             * Sadly they don't, which is why .val is used
             */
            $('#id_body_html').val(templateContent + '<br>' + $containerDiv[0].innerHTML);

            // Make sure both buttons of the same name are set to the loading state
            $('button[name="' + buttonName + '"]').button('loading');

            // No validation needed, remove attachments to prevent unneeded uploading.
            $('[id|=id_attachments]:file').filter(function () {
                return $(inboxCompose).data('formset-disabled') == true;
            }).remove();

            Metronic.blockUI($('.inbox-content'), false, '');

            $form.submit();
        },

        handleTagsAjaxChange: function (tagsAjax) {
            // Select2 doesn't remove certain values (values with quotes), so make sure that the value of the field is correct
            var values = [];
            var data = $(tagsAjax).select2('data');

            for(var i=0; i < data.length; i++) {
                var recipient_data = data[i];
                values.push(recipient_data.id);
            }

            $(tagsAjax).val(values.join());
        },

        getEditor: function() {
            return editor;
        },

        loadDefaultEmailTemplate: function() {
            var self = this;
            var emailAccountId = $(self.config.emailAccountInput).val();

            if (emailAccountId) {
                var url = self.config.defaultEmailTemplateUrl + emailAccountId + '/';

                $.getJSON(url, function(data) {
                    $(self.config.templateField).select2('val', data['template_id']).change();
                });
            }
            else {
                toastr.error('Sorry, I couldn\'t load your default email template. You could try reloading the page');
            }
        },

        setNewEditorValue: function (data, templateChanged) {
            var self = this;
            var htmlPart = data['template'];
            // getValue returns a string, so convert to elements
            var editorValue = $(editor.getValue());
            var currentTemplate = editorValue.closest('#compose-email-template');
            var newEditorValue = '';

            // Check if an email template has already been loaded
            if (currentTemplate.length) {
                if (currentTemplate.html().length) {
                    var changeTemplate = false;

                    if (templateChanged) {
                        // If a different template was selected we want to warn the user
                        changeTemplate = confirm(self.config.overwriteTemplateConfirm);
                    }
                    else {
                        // Template wasn't changed, so a new recipient was entered
                        changeTemplate = true;
                    }

                    if (changeTemplate) {
                        var addedTemplateText = '';

                        if (self.config.currentTemplate) {
                            var diff = {};

                            // First time changing a draft needs a different operation
                            // We want to check if the draft template differs from the default
                            if (self.config.messageType == 'draft' && htmlPart == self.config.currentTemplate) {
                                diff = JsDiff.diffChars(currentTemplate.html(), htmlPart);
                            }
                            else {
                                // Otherwise compare the current editor value with the current template
                                diff = JsDiff.diffChars(currentTemplate.html(), self.config.currentTemplate);
                            }

                            diff.forEach(function (part) {
                                // Get all text that was changed/added
                                if (part.added || part.removed) {
                                    addedTemplateText += part.value;
                                }
                            });
                        }

                        self.config.currentTemplate = htmlPart;

                        // Change the html of the existing email template and add text that was added to the template
                        currentTemplate.html(htmlPart + addedTemplateText);
                        // Since editorValue is actually an array of elements we can't easily convert it back to text
                        var container = $('<div>');
                        // Add the (edited) html to the newly created container
                        container.append(editorValue);
                        // Get the text version of the new html
                        newEditorValue = container[0].innerHTML;
                    }
                }
            }
            else {
                // No email template loaded so create our email template container
                var emailTemplate = '<div id="compose-email-template">' + htmlPart + '</div>';
                // Append the existing text
                newEditorValue = emailTemplate + '<br>' + editor.getValue();

                self.config.currentTemplate = htmlPart;
            }

            // Only overwrite the subject if a new email is being created
            if (this.config.messageType === 'new' && data['template_subject'] != '') {
                $('#id_subject').val(data['template_subject']);
            }

            if (newEditorValue.length) {
                editor.setValue(newEditorValue);
                self.resizeEditor();
                self.processAttachments(data['attachments']);
            }
        },

        processAttachments: function (attachments) {
            var cf = this.config;
            // Clear any existing template attachments
            $(cf.templateAttachmentsDiv).empty();

            var attachmentIds = [];

            for (var i = 0; i < attachments.length; i++) {
                var attachment = attachments[i];

                attachmentIds.push(attachment.id);

                var attachmentRow = $(cf.emptyTemplateAttachmentRow).clone();
                attachmentRow.find(cf.templateAttachmentName).html(attachment.name);
                attachmentRow.find(cf.templateAttachmentId).val(attachment.id);
                attachmentRow.removeAttr('id');
                attachmentRow.removeClass('hidden');

                $(cf.templateAttachmentsDiv).append(attachmentRow);
            }

            $(cf.templateAttachmentIds).val(attachmentIds);
        },

        handleTemplateAttachmentsChange: function (attachmentRow) {
            var self = this,
                cf = self.config;

            var rowAttachmentName = attachmentRow.find(cf.templateAttachmentName);

            if (rowAttachmentName.hasClass('mark-deleted')) {
                rowAttachmentName.removeClass('mark-deleted');
            }
            else {
                rowAttachmentName.addClass('mark-deleted');
            }

            attachmentRow.find('[data-formset-delete-button]').toggleClass('hidden');
            attachmentRow.find('[data-formset-undo-delete]').toggleClass('hidden');

            var newAttachmentIds = [];

            var attachments = $(cf.templateAttachmentRow);
            attachments.each(function () {
                if (!$(this).find(cf.templateAttachmentName).hasClass('mark-deleted')) {
                    var attachmentId = $(this).find(cf.templateAttachmentId).val();
                    if (attachmentId !== "") {
                        // Make sure the value of the empty attachment row doesn't get added
                        newAttachmentIds.push(attachmentId);
                    }
                }
            });

            $(cf.templateAttachmentIds).val(newAttachmentIds);
        },

        setSuccesURL: function(previousState){
            if(previousState != null){
                $("input[name='success_url']").val(previousState);
            }
        }
    }
})(jQuery, window, document);