/* Stable keys keep responses and visible notices in the selected UI language. */
function appMessage(key, values={}) {
 const lang=typeof currentLang==='undefined'?'en':currentLang;
 return (appMessageLocales[lang]?.[key] || appMessageLocales.en[key] || appMessageLocales.en.generic)
  .replace(/\{(\w+)\}/g,(match,name)=>String(values[name] ?? match));
}
function localizeUserMessage(text) {
 if(typeof text==='string' && /^(Failed to fetch|NetworkError|Load failed|The network connection was lost)/i.test(text))return appMessage('error.network_error');
 const key=appMessageAliases[text];
 return key?appMessage(key):text;
}
function serverMessage(data, fallback='generic') {
 return data.message_key?appMessage(data.message_key,data.message_params || {}):
  (data.message?localizeUserMessage(data.message):appMessage(fallback));
}
function updateNotificationTexts() {
 document.querySelectorAll('[data-message]').forEach(node=>node.textContent=appMessage(node.dataset.message));
 const toast=document.querySelector('#snackbar span');
 if(toast)toast.textContent=localizeUserMessage(toast.textContent);
 for(const id of ['appUpdateCheckStatus','appUpdateStatus','updateDesc','diagnosticsStatus','qualityHint','historyStatus']) {
  const node=document.getElementById(id);
  if(node)node.textContent=localizeUserMessage(node.textContent);
 }
}
