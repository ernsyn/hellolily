angular.module('app.contacts').config(contactsConfig);

contactsConfig.$inject = ['$stateProvider'];
function contactsConfig($stateProvider) {
    $stateProvider.state('base.contacts.detail', {
        parent: 'base.contacts',
        url: '/{id:[0-9]{1,}}',
        views: {
            '@': {
                templateUrl: 'contacts/controllers/detail.html',
                controller: 'ContactDetailController',
                controllerAs: 'vm',
            },
        },
        ncyBreadcrumb: {
            label: '{{ contact.full_name }}',
        },
        resolve: {
            currentContact: ['Contact', '$stateParams', function(Contact, $stateParams) {
                var contactId = $stateParams.id;
                return Contact.get({id: contactId}).$promise;
            }],
            caseList: ['Case', '$stateParams', function(Case, $stateParams) {
                return Case.query({filterquery: 'contact.id:' + $stateParams.id, sort: '-created', size: 100}).$promise;
            }],
            dealList: ['Deal', '$stateParams', function(Deal, $stateParams) {
                return  Deal.query({filterquery: 'contact.id:' + $stateParams.id, sort: '-created'}).$promise;
            }],
        },
    });
}

angular.module('app.contacts').controller('ContactDetailController', ContactDetailController);

ContactDetailController.$inject = ['$scope', 'Contact', 'HLResource', 'Settings', 'currentContact',
    'caseList', 'dealList'];
function ContactDetailController($scope, Contact, HLResource, Settings, currentContact,
                                 caseList, dealList) {
    var vm = this;

    vm.contact = currentContact;
    vm.height = 200;

    vm.updateModel = updateModel;

    Settings.page.setAllTitles('detail', currentContact.full_name);
    Settings.page.toolbar.data = {
        model: 'Contact',
        object: currentContact,
        fields: ['first_name', 'preposition', 'last_name'],
        updateCallback: updateModel,
    };

    activate();

    ////

    function activate() {
        vm.caseList = caseList.objects;
        vm.dealList = dealList.objects;
    }

    $scope.$watchCollection('vm.contact.accounts', function() {
        vm.contact.accounts.forEach(function(account) {
            var colleagueList = Contact.search({filterquery: 'NOT(id:' + vm.contact.id + ') AND accounts.id:' + account.id});
            colleagueList.$promise.then(function(response) {
                account.colleagueList = response.objects;
            });
        });

        if (vm.contact.accounts.length >= 2) {
            vm.height = 91;
        }
    });

    function updateModel(data, field) {
        return Contact.updateModel(data, field, vm.contact);
    }
}
