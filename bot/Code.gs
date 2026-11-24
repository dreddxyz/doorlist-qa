const REPORT_URL = 'https://dreddxyz.github.io/doorlist-qa/receipt.json';
const PAGE_URL = 'https://dreddxyz.github.io/doorlist-qa/';
const CODE_URL = 'https://github.com/dreddxyz/doorlist-qa';
function telegram(method, payload) {
  const token = PropertiesService.getScriptProperties().getProperty('TELEGRAM_BOT_TOKEN');
  if (!token) throw Error('Set TELEGRAM_BOT_TOKEN in Script Properties');
  let response;
  try {
    response = UrlFetchApp.fetch('https://api.telegram.org/bot'+token+'/'+method,{
      method:'post',contentType:'application/json',payload:JSON.stringify(payload||{}),muteHttpExceptions:true
    });
  } catch (_) {throw Error('Telegram transport error');}
  const body=JSON.parse(response.getContentText());
  if (!body.ok) {const error=Error(method+' failed: '+body.error_code);error.status=body.error_code;throw error;}
  return body.result;
}
function installDoorlist() {
  const info=telegram('getMe');
  if (telegram('getWebhookInfo').url) throw Error('This bot already has a webhook. Choose a dedicated bot.');
  telegram('setMyCommands',{commands:[{command:'latest',description:'Последний результат CI'},{command:'checks',description:'Какие тесты прошли'},{command:'links',description:'Отчёт и исходники'}]});
  if (!ScriptApp.getProjectTriggers().some(t=>t.getHandlerFunction()==='pollDoorlist')) {
    ScriptApp.newTrigger('pollDoorlist').timeBased().everyMinutes(1).create();
  }
  console.log('Cloud timer installed for @'+info.username);
  pollDoorlist();
}
function receipt() {
  const cache=CacheService.getScriptCache();
  const stored=cache.get('receipt');
  if(stored)return JSON.parse(stored);
  const r=UrlFetchApp.fetch(REPORT_URL,{muteHttpExceptions:true});
  if(r.getResponseCode()!==200) throw Error('Report unavailable');
  const text=r.getContentText();const data=JSON.parse(text);
  if(!Array.isArray(data.suites))throw Error('Invalid receipt');
  cache.put('receipt',text,60);return data;
}
function messageFor(text) {
  const command=(text||'').trim().split(/\s+/)[0].split('@')[0].toLowerCase();
  if(command==='/links')return PAGE_URL+'\n'+CODE_URL;
  if(command!=='/latest' && command!=='/checks')return 'Doorlist QA проверяет кассу тестового концерта.\n/latest — последний результат\n/checks — сценарии по браузерам и API\n/links — отчёт и код';
  let r;
  try {r=receipt();}catch(_){return 'Пока не удалось прочитать опубликованный отчёт. Журнал сборок: '+CODE_URL+'/actions';}
  const testCount=r.suites.reduce((n,s)=>n+s.cases.length,0);
  let lines=[r.ok?'Проверки прошли':'Есть сбои',r.at.slice(0,16).replace('T',' ')+' UTC · '+r.sha.slice(0,7)+' · тестов: '+testCount];
  if(command==='/checks')for(const suite of r.suites){
    lines.push('\n'+suite.suite);
    for(const c of suite.cases)lines.push((c.outcome==='pass'?'✓ ':'× ')+c.name+' ('+c.seconds.toFixed(2)+' с)');
  }
  lines.push(PAGE_URL);return lines.join('\n');
}
function pollDoorlist() {
  const lock=LockService.getScriptLock();
  if(!lock.tryLock(100))return;
  try {
    const props=PropertiesService.getScriptProperties();
    const offset=Number(props.getProperty('NEXT_UPDATE')||0);
    const updates=telegram('getUpdates',{offset:offset,limit:20,timeout:0,allowed_updates:['message']});
    for(const update of updates){
      const m=update.message;
      if(m && m.chat.type==='private' && m.text){
        try {telegram('sendMessage',{chat_id:m.chat.id,text:messageFor(m.text),link_preview_options:{is_disabled:true}});}
        catch(err){if(err.status!==403)throw err;}
      }
      props.setProperty('NEXT_UPDATE',String(update.update_id+1));
    }
  } finally {lock.releaseLock();}
}
