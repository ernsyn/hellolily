angular.module('app.utils.directives').directive('activityAddNote', activityAddNoteDirective);

function activityAddNoteDirective() {
    return {
        restrict: 'E',
        scope: {
            item: '=',
        },
        templateUrl: 'utils/directives/activity_stream_add_note.html',
        controller: ActivityAddNoteController,
        controllerAs: 'vm',
        bindToController: true,
    };
}

ActivityAddNoteController.$inject = ['$http', '$state', 'Note', 'User'];
function ActivityAddNoteController($http, $state, Note, User) {
    var vm = this;
    vm.note = new Note({content_type: vm.item.content_type, object_id: vm.item.id, type: 0});

    vm.addNote = addNote;

    function addNote() {
        if (vm.note.content) {
            vm.note.$save(function(response) {
                // Set user object to note to correctly show profile pic and name
                // when adding a new note in the activity stream.
                User.get({id: currentUser.id}, function(author) {
                    response.author = author;
                });

                vm.item.notes.unshift(response);
                // 'Empty' the note object to be able to continue posting another
                // note without having to refresh the page.
                vm.note = new Note({content_type: vm.item.content_type, object_id: vm.item.id, type: 0});
            });
        } else {
            toastr.error('You can\'t create an empty note!', 'Oops!');
        }
    }
}