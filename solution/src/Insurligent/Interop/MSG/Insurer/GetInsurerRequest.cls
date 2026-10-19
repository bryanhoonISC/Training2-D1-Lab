/// Getinsurer request (IRIS -> insurer). The BO sends the fields as query parameters.
Class Insurligent.Interop.MSG.Insurer.GetInsurerRequest Extends Ens.Request
{

Property IdentityType As %String [ Required ];

Property IdentityNo As %String [ Required ];

Property CompanyCode As %String [ Required ];

}
