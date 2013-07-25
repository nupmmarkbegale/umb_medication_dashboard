define([
  "../../config/resource_locations",
  "models/dose"
], function(Resources, Dose) {
   function AssignedDoses(options) {
    var self = this;

    this.environment = options.environment;
    this.appCode = options.appCode;
    this.user = options.user;
    this.values = [];

    this.fetch = function() {
      var req = $.getJSON(url())
      .done(function(doseHistory) {
        _.each(doseHistory, function(dosesAssignment) {
          self.values.push({
            startDate: isoDate(dosesAssignment),
            doses: doses(dosesAssignment)
          });
        });
      });

      return req;
    };

    function url() {
      return Resources[self.environment].urlRoot + self.appCode + "/participants/" + self.user.id + "/dose_history";
    }

    function isoDate(dosesAssignment) {
      return dosesAssignment.eventDateTime.slice(0, 10);
    }

    function doses(dosesAssignment) {
      return _.map(JSON.parse(dosesAssignment.doses), function(doseAttrs) {
        return new Dose(doseAttrs);
      });
    }
  }

  return AssignedDoses;
});

