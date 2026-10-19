Include %occStatus

/// REST entry point of the lab flow (web application /api/insurligent).
/// POST /api/insurligent/preauth/info with {"search_type":"CID","identity_no":"...","hospital_code":"..."}
Class Insurligent.REST.Router Extends %CSP.REST
{

Parameter CONTENTTYPE = "application/json";

XData UrlMap [ XMLNamespace = "http://www.intersystems.com/urlmap" ]
{
<Routes>
  <Route Url="/preauth/info" Method="POST" Call="PreAuthInfo" />
</Routes>
}

ClassMethod PreAuthInfo() As %Status
{
	// Read the JSON body. IRIS checks [ Required ] and VALUELIST of the class.
	Set tRequest = ##class(Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewRequest).%New()
	Set tSC = tRequest.%JSONImport(%request.Content)
	Set:$$$ISOK(tSC) tSC = tRequest.%ValidateObject()
	Return:$$$ISERR(tSC) ..Reply("400", $System.Status.GetOneErrorText(tSC))
	// Send the request into the production through the business service.
	Set tSC = ##class(Ens.Director).CreateBusinessService("BS.GetPreAuthInfoView", .tService)
	Set:$$$ISOK(tSC) tSC = tService.ProcessInput(tRequest, .tResponse)
	Return:$$$ISERR(tSC) ..Reply("500", $System.Status.GetOneErrorText(tSC))
	Do tResponse.%JSONExport()
	Return $$$OK
}

/// Write an error reply: {"response_code": ..., "response_message": ...}
ClassMethod Reply(pCode As %String, pMessage As %String) As %Status
{
	Set %response.Status = $Select(pCode="400":..#HTTP400BADREQUEST, 1:..#HTTP500INTERNALSERVERERROR)
	Write {"response_code":(pCode), "response_message":(pMessage)}.%ToJSON()
	Return $$$OK
}

}
