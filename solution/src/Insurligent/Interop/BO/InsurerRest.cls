Include %occStatus

/// REST operation (item BO.Insurer.REST) for the private insurer.
/// The MessageMap has one entry: a GetInsurerRequest goes to GetInsurer().
Class Insurligent.Interop.BO.InsurerRest Extends Ens.BusinessOperation
{

Parameter ADAPTER = "EnsLib.HTTP.OutboundAdapter";

Parameter INVOCATION = "Queue";

Property Adapter As EnsLib.HTTP.OutboundAdapter;

XData MessageMap
{
<MapItems>
  <MapItem MessageType="Insurligent.Interop.MSG.Insurer.GetInsurerRequest">
    <Method>GetInsurer</Method>
  </MapItem>
</MapItems>
}

/// Getinsurer: GET <URL setting>/insurer?identity_type=...&identity_no=...&company_code=...
Method GetInsurer(pRequest As Insurligent.Interop.MSG.Insurer.GetInsurerRequest, Output pResponse As Insurligent.Interop.MSG.Insurer.GetInsurerResponse) As %Status
{
	Set pResponse = ##class(Insurligent.Interop.MSG.Insurer.GetInsurerResponse).%New()
	Set tHttp = ##class(%Net.HttpRequest).%New()
	Do tHttp.SetParam("identity_type", pRequest.IdentityType)
	Do tHttp.SetParam("identity_no", pRequest.IdentityNo)
	Do tHttp.SetParam("company_code", pRequest.CompanyCode)
	Set tSC = ..Adapter.SendFormDataArray(.tHttpResponse, "GET", tHttp, , , ..Adapter.URL _ "/insurer")
	// A 404 reply is an error status, but it has a JSON body too: use the body if it is there.
	Return:'$IsObject($Get(tHttpResponse)) tSC
	Return pResponse.%JSONImport(tHttpResponse.Data)
}

}
