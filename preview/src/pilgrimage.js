export const faiths = {
  bloom: { name: "生蓮", gift: "回春", detail: "回復 32 點生命" },
  ward: { name: "持輪", gift: "金身", detail: "抵擋傷害 2.5 秒" },
  pyre: { name: "焚日", gift: "燃魂", detail: "立即充滿神相" },
};

export const route = [
  {
    place: "朱砂渡",
    enemy: "渡口泥傀",
    hp: 100,
    harm: 0.5,
    radius: 2.4,
    brief: "替渡船人取回泥傀銜走的銅鈴。",
    reward: "渡船人敲響銅鈴。河霧散去，對岸露出一列石塔。",
  },
  {
    place: "千塔古道",
    enemy: "巡塔石將",
    hp: 240,
    harm: 0.8,
    radius: 3.2,
    brief: "穿過石塔，奪回通往內殿的日輪印。",
    reward: "石將交出日輪印。封閉多年的內殿終於開啟。",
  },
  {
    place: "日輪神殿",
    enemy: "四臂誓衛",
    hp: 480,
    harm: 1,
    radius: 4,
    brief: "以日輪印喚醒誓衛，讓聖火重回祭壇。",
    reward: "四臂誓衛垂下兵刃。渡口的人們，看見了山頂重燃的聖火。",
  },
];

export function readJourney(raw) {
  try {
    const save = JSON.parse(raw);
    if (
      save?.version === 1 &&
      Object.hasOwn(faiths, save.faith) &&
      Number.isInteger(save.cleared) &&
      save.cleared >= 0 &&
      save.cleared <= route.length
    )
      return { version: 1, faith: save.faith, cleared: save.cleared };
  } catch {}
  return { version: 1, faith: "bloom", cleared: 0 };
}
export function prepareEncounter(state, journey, index) {
  const encounter = route[index];
  state.faith = journey.faith;
  state.boss.doubleStrike = index === 1;
  state.level = journey.cleared + 1;
  state.player.maxHp = state.player.hp = 100 + journey.cleared * 15;
  state.boss.maxHp = state.boss.hp = encounter.hp;
  state.boss.harm = encounter.harm;
  state.boss.slamRadius = encounter.radius;
}
export function invokeGift(state) {
  const p = state.player;
  if (state.status !== "playing" || !state.faith || p.oathCooldown > 0)
    return false;
  if (state.faith === "bloom") p.hp = Math.min(p.maxHp, p.hp + 32);
  if (state.faith === "ward")
    p.invulnerableTimer = Math.max(p.invulnerableTimer, 2.5);
  if (state.faith === "pyre") {
    if (p.aspectTimer > 0 || p.aspect === 100) return false;
    p.aspect = 100;
  }
  p.oathCooldown = 12;
  return true;
}
