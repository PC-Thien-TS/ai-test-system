export type RoleCode = 'N13' | 'N03' | 'N02';

export type RoleDefinition = {
  code: RoleCode;
  name: string;
};

export const roles: Record<RoleCode, RoleDefinition> = {
  N13: {
    code: 'N13',
    name: 'Administrator',
  },
  N03: {
    code: 'N03',
    name: 'Lễ tân',
  },
  N02: {
    code: 'N02',
    name: 'Bác sĩ Nhi',
  },
};

export const roleCodes = Object.keys(roles) as RoleCode[];
