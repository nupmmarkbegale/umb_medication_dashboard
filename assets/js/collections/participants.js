define([
  "backbone",
  "../../config/resource_locations",
  "models/participant",
  "models/participant_action",
  "collections/completed_med_prompts",
  "collections/completed_surveys",
  "collections/sent_messages",
  "collections/clinician_alerts",
  "collections/assigned_doses"
], function(Backbone, Resources, Participant, ParticipantAction, CompletedMedPrompts,
            CompletedSurveys, SentMessages, ClinicianAlerts, AssignedDoses) {
  var Participants = Backbone.Collection.extend({
    initialize: function(models, options) {
      this.environment = options.environment;
      this.medPromptSurvey = options.medPromptSurvey;
      this.surveys = options.surveys;
      this.appCode = options.appCode;
    },

    model: Participant,

    url: function() {
      return Resources[this.environment].urlRoot + this.appCode + "/participants";
    },

    fetchAll: function() {
      var self = this;

      var req = $.getJSON(this.url())
      .then(function(participants) {
        var requests = _.map(participants, function(participantAttrs) {
          var participant = new self.model({
            id: participantAttrs.fields.participant_id,
            first_name: participantAttrs.fields.first_name,
            last_name: participantAttrs.fields.last_name,
            enrollment_date: participantAttrs.fields.enrollment_date
          });
          self.add(participant);

          return [
            self.medPromptSurveysRequest(participant),
            self.surveysRequest(participant),
            self.messagesRequest(participant),
            self.alertsRequest(participant),
            self.latestActionRequest(participant),
            self.doseHistoryRequest(participant)
          ];
        });

        return $.when.apply(this, _.flatten(requests));
      });

      return req.then(function() { return self; });
    },

    medPromptSurveysRequest: function(participant) {
      participant.medPromptSurveys = new CompletedMedPrompts([], {
        environment: this.environment,
        appCode: this.appCode,
        user: participant,
        survey: this.medPromptSurvey
      });

      return participant.medPromptSurveys.fetch({ parse: true });
    },

    surveysRequest: function(participant) {
      var self = this;
      participant.surveys = {};
      var requests = _.map(this.surveys, function(survey) {
        participant.surveys[survey.name] = new CompletedSurveys([], {
          environment: self.environment,
          appCode: self.appCode,
          user: participant,
          survey: survey
        });

        return participant.surveys[survey.name].fetch({ parse: true });
      });

      return requests;
    },

    messagesRequest: function(participant) {
      participant.messages = new SentMessages([], {
        environment: this.environment,
        appCode: this.appCode,
        user: participant
      });

      return participant.messages.fetch({ parse: true });
    },

    alertsRequest: function(participant) {
      participant.clinicianAlerts = new ClinicianAlerts([], {
        environment: this.environment,
        appCode: this.appCode,
        user: participant
      });

      return participant.clinicianAlerts.fetch({ parse: true });
    },

    latestActionRequest: function(participant) {
      participant.setLatestAction(new ParticipantAction({}, {
        environment: this.environment,
        appCode: this.appCode,
        user: participant
      }));

      return participant.getLatestAction().fetch({ parse: true });
    },

    doseHistoryRequest: function(participant) {
      participant.setAssignedDoses(new AssignedDoses({
        environment: this.environment,
        appCode: this.appCode,
        user: participant
      }));

      return participant.getAssignedDoses().fetch();
    }
  });

  return Participants;
});
