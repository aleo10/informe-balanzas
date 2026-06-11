-- Ejecutar en Supabase → SQL Editor

create table clientes (
  id               bigint generated always as identity primary key,
  razon_social     text not null,
  direccion        text default '',
  localidad        text default ''
);

create table balanzas (
  id                       bigint generated always as identity primary key,
  razon_social             text default '',
  localidad_cliente        text default '',
  tipo_balanza             text default '',
  mod_indicador            text default '',
  marca                    text default '',
  n_serie_indicador        text default '',
  cod_aprobacion_indicador text default '',
  ubicacion                text default '',
  plataforma               text default '',
  medidas                  text default '',
  n_serie_plataforma       text default '',
  cod_aprobacion_plataforma text default '',
  ult_verificacion         text default '',
  cap_max_kg               text default '',
  cap_min_kg               text default '',
  div_min_kg               text default '',
  apoyos                   text default '',
  cod_interno              text unique not null,
  precintos_ant_plataforma text default '',
  precintos_vig_plataforma text default '',
  precintos_ant_indicador  text default '',
  precintos_vig_indicador  text default ''
);

create table configuracion (
  clave text primary key,
  valor text default ''
);

-- Datos iniciales de configuración (certificados de pesas)
insert into configuracion (clave, valor) values
  ('cert_pesas_pequenas', ''),
  ('desc_pesas_pequenas', ''),
  ('cert_pesas_grandes',  ''),
  ('desc_pesas_grandes',  '');

-- Deshabilitar RLS (Row Level Security) para acceso simple con anon key
alter table clientes      disable row level security;
alter table balanzas      disable row level security;
alter table configuracion disable row level security;
