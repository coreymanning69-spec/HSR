// Public-result presentation only. Hand counts select choreography, never legality.
export const STAFF_SOCKETS = Object.freeze({
  plain: {length:54, grip:12}, runed:{length:60, grip:10},
  weathered:{length:50, grip:9}, ceremonial:{length:64, grip:14}, heavy:{length:58, grip:16},
});
export const staffSockets = style => STAFF_SOCKETS[style] || STAFF_SOCKETS.plain;
// Wands share the staff shape and tip contract, with a short one-handed shaft.
export function focusSockets(weapon, style = 'plain') {
  const staff = staffSockets(style);
  return weapon === 'wand' ? {length: staff.length * .42, grip: 0} : staff;
}
export const isCastingImplement = (weapon, casting) => ['staff','wand'].includes(weapon) && casting?.source !== 'hands';
export function castingProfile(receipt = {}) {
  const spec=receipt.ruling || {}, authored=spec.presentation?.casting || {}, visual=receipt.presentation?.casting || {};
  const valid=(key,values) => [visual[key],authored[key]].find(value=>values.includes(value));
  const type=String(visual.element || receipt.damageType || receipt.damage_type || spec.damage_type || '').toLowerCase();
  const heal=Number(receipt.healing)>0 || visual.element==='heal' || spec.operation==='heal' || spec.effect==='heal' || spec.effect==='healing';
  const stance=valid('stance',['aim','gather','overhead','ward','mend']) ||
    (heal?'mend':spec.radius?'overhead':spec.condition?'ward':type==='lightning'?'aim':type==='force'?'gather':'aim');
  const hands=valid('hands',[1,2]) || (['gather','overhead','ward'].includes(stance)?2:1);
  const source=valid('source',['hands','implement','auto']) ||
    (receipt.type==='staff_cast'?'implement':receipt.type==='cast'?'hands':'auto');
  return {stance,hands,source,element:heal?'heal':type||'force',
    delivery:stance==='mend'?'orb':type==='lightning'?'beam':stance==='overhead'?'orb':'bolt'};
}
