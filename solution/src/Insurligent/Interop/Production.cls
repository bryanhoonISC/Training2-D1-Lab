/// Lab production: GetPreAuthInfo_View with PAT-01 (HL7) and Getinsurer (REST) only.
Class Insurligent.Interop.Production Extends Ens.Production
{

XData ProductionDefinition
{
<Production Name="Insurligent.Interop.Production" TestingEnabled="true" LogGeneralTraceEvents="false">
  <Description>Lab: GetPreAuthInfo_View with PAT-01 and Getinsurer only.</Description>
  <ActorPoolSize>2</ActorPoolSize>
  <Item Name="BS.GetPreAuthInfoView" Category="PreAuth" ClassName="Insurligent.Interop.BS.D1FrontService" PoolSize="0" Enabled="true" Foreground="false" Comment="Called by Insurligent.REST.Router (POST /api/insurligent/preauth/info)" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="TargetConfigName">BP.GetPreAuthInfoView</Setting>
  </Item>
  <Item Name="BP.GetPreAuthInfoView" Category="PreAuth" ClassName="Insurligent.Interop.BP.GetPreAuthInfoView" PoolSize="1" Enabled="true" Foreground="false" Comment="Main BP: PAT-01 through BP.HIS.Patient, then Getinsurer" LogTraceEvents="false" Schedule="">
  </Item>
  <Item Name="BP.HIS.Patient" Category="PreAuth" ClassName="Insurligent.Interop.BP.HISPatient" PoolSize="1" Enabled="true" Foreground="false" Comment="Sub-BP: one PAT-01 query" LogTraceEvents="false" Schedule="">
  </Item>
  <Item Name="BO.HIS.HL7" Category="PreAuth" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true" Foreground="false" Comment="HL7 V2.5.1 to the HIS over MLLP (container mock_his)" LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">mock_his</Setting>
    <Setting Target="Adapter" Name="Port">2575</Setting>
  </Item>
  <Item Name="BO.Insurer.REST" Category="PreAuth" ClassName="Insurligent.Interop.BO.InsurerRest" PoolSize="1" Enabled="true" Foreground="false" Comment="REST to the insurer (container mock_insurer)" LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="HTTPServer">mock_insurer</Setting>
    <Setting Target="Adapter" Name="HTTPPort">8080</Setting>
    <Setting Target="Adapter" Name="URL">/api</Setting>
  </Item>
</Production>
}

}
