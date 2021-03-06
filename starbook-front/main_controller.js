angular.module('myApp')
  .controller('mainCtrl', ['$scope', '$http', 'api', 'ENV', '$timeout', '$window', '$cookies', '$mdDialog', '$mdToast',
    'authService',
    function($scope, $http, api, ENV, $timeout, $window, $cookies, $mdDialog, $mdToast, authService) {
      var auth2;
      var self = this;
      var starbook_token = 'starbook-token';

      self.auth = true;

      gapi.load('auth2', function() {

        if (ENV.SEND_COOKIES) {
          auth2 = gapi.auth2.init({
            client_id: ENV.GOOGLE_SIGN_IN_CLIENT_ID,
            cookiepolicy: 'single_host_origin'
            // Request scopes in addition to 'profile' and 'email'
            //scope: 'additional_scope'
          });

          auth2.then(function() {
            $timeout(function() {
              self.auth = auth2.isSignedIn.get();
              if (self.auth) {
                window.globalVar = window.globalVar || {};
                var basicProfile = auth2.currentUser.get().getBasicProfile();
                window.globalVar.looged_user_email = basicProfile.getEmail();
                window.globalVar.logged_image = basicProfile.getImageUrl();
                authService.saveToken(auth2);
                api.tree().success(function(response) {
                  self.email = auth2.currentUser.get().getBasicProfile().getEmail();
                  api.get_role().success(function(role) {
                    self.role = role;
                  });
                  populateGraph(response);
                }).error(function() {
                  self.auth = false;
                });
              }
            });
          })
        } else {
          api.tree().success(function(response) {
            populateGraph(response);
          })
        }
      });

      self.signIn = function() {
        auth2.signIn().then(function() {
          $timeout(function() {
            authService.saveToken(auth2);
            $window.location.reload();
          });
        });
      };

      self.signOut = function() {
        auth2.signOut().then(function() {
          $timeout(function() {
            $cookies.remove(starbook_token);
            $window.location.reload();
          });
        });
      };

      self.meClicked = function() {
        if (self.email) {
          globalVar.updateBy({ email: self.email });
        }
      };

      self.updatePerson = function(ev) {
        closeSideBar();
        $mdDialog.show({
          controller: 'UpdatePersonController',
          controllerAs: 'ctrl',
          templateUrl: 'assets/update_person_template.html',
          parent: angular.element(document.body),
          targetEvent: ev,
          clickOutsideToClose: true
        }).then(function(fields) {
          fields['email'] = window.globalVar.currentUser.email;
          return api.update(fields);
        }).then(function() {
          $mdToast.showSimple('Person updated successfully');
          toggleSideBar();
        }, function() {
          $mdToast.showSimple('Failed to update person');
          toggleSideBar();
        })

      };

      self.addPerson = function(ev) {
        closeSideBar();
        $mdDialog.show({
          controller: 'AddPersonController',
          controllerAs: 'ctrl',
          templateUrl: 'assets/add_person_template.html',
          parent: angular.element(document.body),
          targetEvent: ev,
          clickOutsideToClose: true
        }).then(function(fields) {
          return api.add_person(fields);
        }).then(function() {
          $mdToast.showSimple('Person added successfully');
          toggleSideBar();
        }, function() {
          $mdToast.showSimple('Failed to add person');
          toggleSideBar();
        })
      };

      self.editTitle = function() {
        var newTitle;
        var confirm = $mdDialog.prompt()
          .title('Edit Title')
          .initialValue(window.globalVar.currentUser.title)
          .placeholder('Title')
          .ok('Submit')
          .cancel('Cancel');
        $mdDialog.show(confirm).then(function(result) {
          var email = window.globalVar.currentUser.email;
          newTitle = result;
          return api.update({ email: email, title: result });
        }).then(function() {
          window.globalVar.currentUser.title = newTitle;
          var userTitle = document.getElementsByClassName("user-title")[0];
          userTitle.textContent = newTitle;
        }, function() {
          // user canceled
        });
      };

      self.editPhone = function() {
        if (globalVar.currentUser.email !== globalVar.looged_user_email) {
          return;
        }
        var newPhone;
        var confirm = $mdDialog.prompt()
          .title('Edit Phone')
          .initialValue(window.globalVar.currentUser.phone)
          .placeholder('Phone')
          .ok('Submit')
          .cancel('Cancel');
        $mdDialog.show(confirm).then(function(result) {
          var email = window.globalVar.currentUser.email;
          newPhone = result;
          return api.update({ email: email, phone: result });
        }).then(function() {
          window.globalVar.currentUser.phone = newPhone;
          var userPhone = document.getElementsByClassName("user-phone")[0];
          userPhone.textContent = newPhone;
        }, function() {
          // user canceled
        });
      };

      self.choosePic = function(ev) {
        if (globalVar.currentUser.email !== globalVar.looged_user_email) {
          return;
        }

        closeSideBar();
        $mdDialog.show({
          controller: 'ChoosePicController',
          controllerAs: 'ctrl',
          templateUrl: 'assets/choose_pic_modal.html',
          parent: angular.element(document.body),
          targetEvent: ev,
          clickOutsideToClose: true
        }).then(function(imageUrl) {
          return api.update({ email: window.globalVar.currentUser.email, image: imageUrl });
        }).then(function() {
          $mdToast.showSimple('Picture chosen');
          toggleSideBar();
        }, function() {
          toggleSideBar();
        })
      };

    }]);
