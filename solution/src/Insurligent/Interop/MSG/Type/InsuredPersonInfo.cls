/// The "insured_person" object of the Getinsurer reply. A serial object is stored
/// inside the message that contains it.
Class Insurligent.Interop.MSG.Type.InsuredPersonInfo Extends (%SerialObject, %JSON.Adaptor)
{

Property InsurerId As %String(%JSONFIELDNAME = "insurer_id");

Property CitizenId As %String(%JSONFIELDNAME = "insurer_citizenId");

Property PassportId As %String(%JSONFIELDNAME = "insurer_passportId");

Property Title As %String(%JSONFIELDNAME = "insurer_title");

Property FirstName As %String(%JSONFIELDNAME = "insurer_firstname");

Property LastName As %String(%JSONFIELDNAME = "insurer_lastName");

Property Gender As %String(%JSONFIELDNAME = "insurer_gender");

/// The insurer sends a JSON number here, so the type is %Integer.
Property Age As %Integer(%JSONFIELDNAME = "insurer_age");

}
