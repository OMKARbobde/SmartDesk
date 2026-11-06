from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.fields import ErrorDetail


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate(self, attrs):
        User = get_user_model()
        identifier = attrs["identifier"]
        user = User.objects.filter(username=identifier).first()

        if user is None:
            matches = list(User.objects.filter(email__iexact=identifier).only("pk", "username")[:2])
            if len(matches) > 1:
                # Email is not unique in the existing schema. This application-level check
                # cannot prevent concurrent account changes from creating a new ambiguity.
                raise serializers.ValidationError({
                    "identifier": ErrorDetail(
                        "This email matches multiple accounts.",
                        code="ambiguous_identifier",
                    )
                })
            if matches:
                user = matches[0]

        username = user.get_username() if user is not None else identifier
        authenticated_user = authenticate(
            request=self.context.get("request"),
            username=username,
            password=attrs["password"],
        )
        if authenticated_user is None:
            raise AuthenticationFailed("The supplied credentials are invalid.")

        attrs["user"] = authenticated_user
        return attrs


class CurrentUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    employee_profile_id = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "role",
            "employee_profile_id",
        )
        read_only_fields = fields

    def get_display_name(self, user):
        return " ".join(part for part in (user.first_name, user.last_name) if part).strip() or user.username

    def get_employee_profile_id(self, user):
        try:
            return user.employee_profile.pk
        except ObjectDoesNotExist:
            return None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email")

    def validate(self, attrs):
        allowed = set(self.fields)
        forbidden = set(self.initial_data.keys()) - allowed
        if forbidden:
            raise serializers.ValidationError({
                field: ["This field may not be changed through the profile endpoint."]
                for field in sorted(forbidden)
            })

        email = attrs.get("email")
        if email:
            User = get_user_model()
            # The existing User.email field is not unique. This friendly
            # pre-check prevents ordinary duplicate edits but cannot serialize
            # concurrent account changes without a database uniqueness constraint.
            duplicate = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists()
            if duplicate:
                raise serializers.ValidationError({"email": ["This email is already associated with another account."]})
        return attrs
