define(["backbone"], function(Backbone) {
  var CompletedMedPrompt = Backbone.Model.extend({
    COLUMN_PREFIX_LENGTH: "FEATURE_VALUE_DT_".length,

    parse: function(data, options) {
      var self = this,
          parsed = {};

      _.each(data.fields, function(v, k) {
        var attr = k.substr(self.COLUMN_PREFIX_LENGTH);

        parsed[attr] = v;
      });

      return parsed;
    },

    doseTime: function() {
      return this.get("doseTime");
    },

    date: function() {
      return this.get("date");
    },

    nonadherenceDueToSideEffects: function() {
      return (this.get("reason_for_missing") === "It makes me feel bad.") ? this.get("date") : false;
    }
  });

  return CompletedMedPrompt;
});
