
// TODO: set focus on first element a form error was detected    
// TODO: select first e-mail as primary when deleting primary

$(document).ready(function() {
    // set focus on first name
    set_focus('id_first_name'); 
    
    // manually add hover classes when hovering over a label element
    $('.email_is_primary label span').live({
        mouseenter: function() {
            $(this).addClass('state-hover');
        },
        mouseleave: function() {
            $(this).removeClass('state-hover');
        }
    });
    
    // change selected primary e-mailadres
    $('.email_is_primary label span').live('click', function() {
    	// find elements
        formset = $(this).closest('.mws-form-row');
        input_siblings = $(formset).find('.email_is_primary label input');
        
        // uncheck others
        $(input_siblings).siblings('span').removeClass('checked');
        
        // check this one
        $(this).addClass('checked');
    })
    
    // show or hide 'other'-options on page load or when the value changes
    $('select.other:visible').each(function() {
        show_or_hide_other_option($(this)[0], true);
    }).live('change', function() {
        show_or_hide_other_option($(this)[0]);
    });
    
    // delete contact
    $('#delete-contact-dialog-link').click(function(event) {
        $('#delete-contact-form-dialog').dialog('open');
        event.preventDefault();
    });
    // transform div into delete dialog
    $('#delete-contact-form-dialog').dialog({
        autoOpen: false,
        title: gettext('Delete contact'),
        modal: true,
        width: 350,
        buttons: [
            { 
                'class': 'mws-button red float-left',
                text: gettext('No'),
                click: function() {
                    // cancel form on NO
                    $(this).dialog('close');
                }
            },
            {
                'class': 'mws-button green',
                text: gettext('Yes'),
                click: function() {
                    // submit form on YES
                    $(this).find('form').submit();
                }
            }
        ]
    });
    
    // enable formsets for email addresses, phone numbers and addresses
    form_prefices = {'email_addresses': gettext('Add an e-mail address'), 'phone_numbers': gettext('Add a phone number'), 'addresses': gettext('Add an address')};    
    for(form_prefix in form_prefices) {
        $('.' + form_prefix + '-mws-formset').formset( {
            formTemplate: $('#' + form_prefix + '-form-template'), // needs to be unique per formset
            prefix: form_prefix, // needs to be unique per formset
            addText: form_prefices[form_prefix],
            formCssClass: form_prefix, // needs to be unique per formset
            addCssClass: form_prefix + '-add-row', // needs to be unique per formset
            deleteCssClass: form_prefix + '-delete-row', // needs to be unique per formset
            notEmptyFormSetAddCssClass: 'mws-form-item'
        });
    };
    
    // auto grow description 
    $('#id_description').elastic();
    
    // update e-mail formset to select first as primary
    // $('.email_is_primary input[name$="primary-email"]:first').attr('checked', 'checked').siblings('span').addClass('checked');
});
