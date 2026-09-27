/* Shared presentation helpers. All mechanics arrive from public_view. */
(function (global) {
  'use strict';
  const escape = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const list = value => Array.isArray(value) ? value : [];
  const affixName = value => typeof value === 'string' ? value : value?.name;
  const hidden = item => item.kind === 'imprint' && !item.identified;
  function normalize(value) {
    const item = typeof value === 'string' ? {name:value} : {...(value || {})};
    if (hidden(item)) return {id:item.id, name:item.name || 'Unidentified Rune', kind:'imprint', identified:false, slot:item.slot, rarity:'unknown', level:item.level, temporary:true};
    return item;
  }
  function name(value) {
    const item=normalize(value);
    return item.display_name || item.name || item.id || 'Item';
  }
  function gear(actor) {
    const raw=actor?.equipment || [];
    return Array.isArray(raw) ? raw.map(normalize) : Object.entries(raw).map(([slot,item])=>({...normalize(item),slot}));
  }
  function image(item, base='web/assets/') {
    item=normalize(item);
    const key=String(item.name || '').toLowerCase();
    const file=hidden(item)?'unidentified-rune':key==='longsword'?'longsword':key==='chain shirt'?'chain-shirt':null;
    return file ? `<img class="item-art" src="${escape(base+file+'.png')}" alt="${escape(hidden(item)?'Neutral unidentified Rune illustration':key+' base illustration')}" loading="lazy">` : `<span class="item-art art-fallback" role="img" aria-label="No illustration available">◇<small>Art pending</small></span>`;
  }
  function numbers(item) {
    item=normalize(item); if(hidden(item)) return [];
    const rows=[];
    if(item.damage_dice) rows.push(['Damage dice',item.damage_dice+(item.damage_modifier?`${item.damage_modifier>0?'+':''}${item.damage_modifier}`:'')]);
    else if(item.base_damage) rows.push(['Base damage',item.base_damage+' fixed']);
    if(item.damage_dice || item.base_damage) rows.push(['Weapon attack bonus',item.attack_bonus ?? 'Not reported']);
    for(const [key,label] of [['base_ac','Base AC'],['ac_bonus','AC bonus'],['shield_bonus','Shield bonus'],['density','Density ×'],['dex_cap','Dexterity cap'],['level','Level'],['value','Value'],['weight','Weight'],['percentage_bonus','Bonus %']]) {
      if(item[key]!=null && (item[key]!==0 || key==='dex_cap' || key==='value')) rows.push([label,item[key]]);
    }
    if(item.damage_dice || item.base_damage) {if(item.reach!=null) rows.push(['Reach',item.reach+' ft']);if(item.range_normal>5) rows.push(['Range',`${item.range_normal} / ${item.range_long} ft`]);}
    return rows;
  }
  const rows = pairs => `<dl class="item-stats">${pairs.map(([key,val])=>`<div><dt>${escape(key)}</dt><dd>${escape(val)}</dd></div>`).join('')}</dl>`;
  function affixes(item) {
    if(hidden(item)) return '<p class="muted">Prefix and suffix are unrevealed.</p>';
    return `<div class="affix-chips">${['prefix','suffix'].map(kind=>`<span><small>${kind}</small>${escape(affixName(item[kind]) || (Object.hasOwn(item,kind)?'None':'Not reported'))}</span>`).join('')}</div>`;
  }
  function effect(e) {
    const details=[];
    if(e.condition && e.condition!=='always') details.push('When '+e.condition.replaceAll('_',' '));
    if(e.flat_bonus) details.push(`${e.flat_bonus>0?'+':''}${e.flat_bonus} magnitude`);
    if(e.multiplier!=null && e.multiplier!==1) details.push('×'+e.multiplier+' magnitude');
    if(e.per_stack_bonus) details.push(`${e.per_stack_bonus} per stack of ${e.per_stack_source}`);
    if(list(e.applies_to_tags).length) details.push('Applies to '+e.applies_to_tags.join(', '));
    if(list(e.grants_tags).length) details.push('Grants '+e.grants_tags.join(', '));
    if(e.inflicts_status) details.push(`${e.inflicts_status} · ${e.status_duration} turns · potency ${e.status_potency ?? 1}`);
    if(list(e.blocks_statuses).length) details.push('Blocks '+e.blocks_statuses.join(', '));
    if(e.opens_gate) details.push('Opens '+e.opens_gate);
    if(e.closes_gate) details.push('Closes '+e.closes_gate);
    if(e.charges!=null) details.push(e.charges+' charges');
    if(e.scope) details.push(e.scope);
    if(e.duration && e.duration!=='permanent') details.push(e.duration.replaceAll('_',' '));
    if(e.stack_group) details.push('stack group: '+e.stack_group);
    const source = e.source?.name ? ` · source: ${e.source.name}` : '';
    const status = e.status && e.status!=='active' ? ` · ${e.status}` : '';
    const explanation = e.summary || details.join(' · ') || e.description || 'No additional details reported.';
    return `<li><strong>${escape(e.name)}</strong><small>${escape([e.phase,e.direction].filter(Boolean).join(' · '))}${escape(source)}${escape(status)}</small><p>${escape(explanation)}</p>${e.reason?`<small>${escape(e.reason)}</small>`:''}</li>`;
  }
  function card(value, attr, index, base) {
    const item=normalize(value);
    return `<button class="item-card" data-${attr}="${escape(index)}" data-item-id="${escape(item.id||item.name)}" data-rarity="${escape(item.rarity || 'common')}">${image(item,base)}<span class="item-card-body"><small>${escape(item.slot || item.kind || 'Equipment')} · ${escape(item.rarity || item.tier || 'Unreported tier')}</small><strong>${escape(name(item))}</strong>${affixes(item)}<span class="item-summary">${escape(numbers(item).slice(0,2).map(([k,v])=>k+': '+v).join(' · ') || (hidden(item)?'Identify to reveal properties':'Inspect details'))}</span></span></button>`;
  }
  function detail(value, base) {
    const item=normalize(value);
    const effects=list(item.effect_explanations).length ? list(item.effect_explanations) : [...list(item.inherent),...list(item.prefix?.effects),...list(item.suffix?.effects)];
    return `<div class="item-detail-head">${image(item,base)}<div><p class="eyebrow">${escape(item.slot||item.kind||'Equipment')}</p><h3>${escape(name(item))}</h3><p>${escape(item.flavor||item.description||(hidden(item)?'Identify this Rune through an available service to reveal its properties.':'No description reported.'))}</p></div></div>${affixes(item)}${rows(numbers(item))}${hidden(item)?'':`<p class="muted">${escape(list(item.tags).join(' · '))}</p>${['prefix','suffix'].map(k=>item[k]?.description?`<p><strong>${k}:</strong> ${escape(item[k].description)}</p>`:'').join('')}${['prefix','suffix'].map(k=>item[k]?.effect?'<p>'+escape(k+': '+item[k].effect+' '+item[k].value)+'</p>':'').join('')}${item.critical_dice?'<p>Critical dice: '+escape(item.critical_dice)+'</p>':''}${Object.keys(item.alternate_modes||{}).length?'<h3>Alternate attack modes</h3><pre>'+escape(JSON.stringify(item.alternate_modes,null,2))+'</pre>':''}${effects.length?'<h3>Effects and conditions</h3><ul class="item-effects">'+effects.map(effect).join('')+'</ul>':''}${list(item.modifiers).length?'<h3>Rune modifiers</h3>'+rows(item.modifiers.map(m=>[m.effect,m.value])):''}${list(item.appearance).length?'<h3>Observed appearance</h3><p>'+item.appearance.map(escape).join('<br>')+'</p>':''}${list(item.utility_uses).length?'<h3>Utility</h3><p>'+item.utility_uses.map(escape).join(' · ')+'</p>':''}`}<p class="muted">${item.temporary?'Temporary item':'Base equipment'} · Artwork is illustrative; listed properties describe this instance.</p><details><summary>Public item data</summary><pre>${escape(JSON.stringify(item,null,2))}</pre></details>`;
  }
  function examineDetail(value, skillDescriptions) {
    const data=value||{};
    const statRows=list(data.stats).map(row=>[row.label,row.value]);
    const scoreRows=data.ability_scores ? Object.entries(data.ability_scores).map(([key,val])=>[key,`${val} (${data.ability_modifiers?.[key]>=0?'+':''}${data.ability_modifiers?.[key]??'—'})`]) : [];
    const effectRows=list(data.effects).map(effect);
    const contributors=list(data.contributors).map(row=>`<li><strong>${escape(row.source||row.name||'Source')}</strong><span>${escape([row.value,row.stat,row.operation].filter(value=>value!=null&&value!=='').join(' · '))}</span></li>`).join('');
    const skillDescMap=skillDescriptions||{};
    const skillRows=data.skills&&Object.keys(data.skills).length?`<h3>Skills</h3><dl class="item-stats">${Object.entries(data.skills).map(([skill,val])=>{const desc=skillDescMap[skill]||'';const title=desc?` title="${escape(desc)}"`:''
;return `<div${title}><dt>${escape(skill)}</dt><dd>${escape(val)}</dd></div>`;}).join('')}</dl>`:'';
    return `<div class="item-detail-head"><span class="item-art art-fallback" role="img" aria-label="Examine detail">⌕<small>Examine</small></span><div><p class="eyebrow">${escape(data.entity_type||'detail')}</p><h3>${escape(data.name||'Examine')}</h3><p>${escape(data.short||'No public explanation reported.')}</p></div></div>${scoreRows.length?`<h3>Ability scores</h3>${rows(scoreRows)}`:''}${statRows.length?rows(statRows):''}${skillRows}${data.features?.length?`<h3>Features</h3><p>${escape(data.features.join(' · '))}</p>`:''}${data.conditions?.length?`<h3>Conditions</h3><p>${escape(data.conditions.join(' · '))}</p>`:''}${effectRows.length?`<h3>Active effects</h3><ul class="item-effects">${effectRows.join('')}</ul>`:''}${contributors?`<h3>Result contributors</h3><ul class="item-effects">${contributors}</ul>`:''}${data.suppressed?.length?`<h3>Suppressed effects</h3><ul class="item-effects">${data.suppressed.map(row=>`<li><strong>${escape(row.effect||'Effect')}</strong><p>${escape(row.reason||'Suppressed by stacking rules.')}</p></li>`).join('')}</ul>`:''}${data.stacking_notes?.length?`<p class="muted">${escape(data.stacking_notes.join(' · '))}</p>`:''}`;
  }
  function slots(view, actorId) {
    const equipped=view.imprints?.[actorId] || {};
    return `<div class="imprint-slots">${['helmet','necklace','cloak','torso','ring_1','ring_2','legs','boots'].map(slot=>{const id=equipped[slot];const item=id ? list(view.inventory).find(i=>i.id===id) : null;return `<div><small>${escape(slot.replace('_',' '))}</small><span>${escape(item?name(item):id||'Empty')}</span></div>`}).join('')}</div>`;
  }
  global.HSRUI={escape,normalize,name,gear,image,numbers,affixes,card,detail,examineDetail,slots};
})(globalThis);
