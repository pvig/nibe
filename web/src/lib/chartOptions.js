// Factory d'options ApexCharts partagées entre les composants graphiques

export const SHUTTER_COLORS = {
  salon: '#f97316',
  bureau: '#a855f7',
  cuisine: '#ec4899',
  chambre: '#06b6d4'
};
export const DEFAULT_COLORS = ['#22c55e', '#eab308', '#38bdf8', '#f43f5e'];

export const apexTheme = { mode: 'dark', palette: 'palette1' };

export const apexGrid = {
  borderColor: 'rgba(255,255,255,0.06)',
  strokeDashArray: 3
};

export function makeToolbar() {
  return {
    show: true,
    tools: { download: true, selection: true, zoom: true, zoomin: true, zoomout: true, pan: true, reset: true },
    autoSelected: 'zoom'
  };
}

export function makeLocale() {
  return {
    defaultLocale: 'fr',
    locales: [{
      name: 'fr',
      options: {
        toolbar: {
          download: 'Télécharger SVG',
          selection: 'Sélection',
          selectionZoom: 'Zoom par sélection',
          zoomIn: 'Zoom +',
          zoomOut: 'Zoom -',
          pan: 'Déplacer',
          reset: 'Réinitialiser'
        }
      }
    }]
  };
}
