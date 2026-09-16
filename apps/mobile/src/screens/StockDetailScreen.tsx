import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { colors } from '../theme/colors';
import { fetchApi } from '../api/client';

export default function StockDetailScreen({ route, navigation }: any) {
  const { symbol } = route.params;
  const [activeTab, setActiveTab] = useState('Overview');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Re-using the same endpoints as web
      const quote = await fetchApi(`/stocks/${symbol}/quote`);
      const analysis = await fetchApi(`/stocks/${symbol}/analysis`);
      setData({ quote, analysis });
    } catch (e) {
      console.warn(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <View style={[styles.container, { justifyContent: 'center' }]}><ActivityIndicator size="large" color={colors.accentBlue} /></View>;
  }

  if (!data) {
    return <View style={styles.container}><Text style={{color: 'white', padding: 20}}>Failed to load data</Text></View>;
  }

  const { quote, analysis } = data;

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.symbol}>{symbol}</Text>
        <View style={styles.priceCol}>
          <Text style={styles.price}>₹{quote?.ltp?.toFixed(2) || '—'}</Text>
          <Text style={[styles.change, { color: quote?.change_pct >= 0 ? colors.accentGreen : colors.accentRed }]}>
            {quote?.change_pct >= 0 ? '+' : ''}{quote?.change_pct?.toFixed(2) || '0'}%
          </Text>
        </View>
      </View>

      <View style={styles.tabsRow}>
        {['Overview', 'Technical', 'Entry Zones'].map(tab => (
          <TouchableOpacity 
            key={tab} 
            style={[styles.tab, activeTab === tab && styles.tabActive]}
            onPress={() => setActiveTab(tab)}
          >
            <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>{tab}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={styles.content}>
        {activeTab === 'Overview' && (
          <View>
            <View style={styles.card}>
              <Text style={styles.cardHeader}>AI Opportunity</Text>
              <Text style={[styles.highBadge, { color: analysis?.opportunity_level === 'HIGH' ? colors.accentGreen : colors.accentYellow }]}>
                {analysis?.opportunity_level || 'UNKNOWN'} ({(analysis?.confidence * 100).toFixed(0)}%)
              </Text>
            </View>
            <TouchableOpacity 
              style={styles.debateBtn}
              onPress={() => navigation.navigate('AgentDebate', { symbol, analysis })}
            >
              <Text style={styles.debateBtnText}>View Full Agent Debate →</Text>
            </TouchableOpacity>
          </View>
        )}
        
        {activeTab === 'Entry Zones' && (
          <View style={styles.card}>
            <Text style={styles.cardHeader}>Zone A (Primary)</Text>
            <Text style={styles.zonePrice}>₹{analysis?.opportunity_state?.entry_zones?.[0]?.min_price || '—'} - ₹{analysis?.opportunity_state?.entry_zones?.[0]?.max_price || '—'}</Text>
            <Text style={styles.zoneDesc}>{analysis?.opportunity_state?.entry_zones?.[0]?.rationale || 'Waiting for setup.'}</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', padding: 20 },
  symbol: { fontSize: 32, fontWeight: 'bold', color: colors.textPrimary },
  priceCol: { alignItems: 'flex-end' },
  price: { fontSize: 24, fontWeight: 'bold', color: colors.textPrimary },
  change: { fontSize: 14, color: colors.accentGreen, fontWeight: 'bold' },
  tabsRow: { flexDirection: 'row', borderBottomWidth: 1, borderColor: colors.border },
  tab: { padding: 16, flex: 1, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderColor: colors.accentBlue },
  tabText: { color: colors.textSecondary, fontWeight: '600' },
  tabTextActive: { color: colors.accentBlueBright },
  content: { padding: 20 },
  card: { backgroundColor: colors.bgCard, padding: 20, borderRadius: 12, borderWidth: 1, borderColor: colors.border, marginBottom: 16 },
  cardHeader: { color: colors.textMuted, fontSize: 12, fontWeight: 'bold', textTransform: 'uppercase', marginBottom: 10 },
  highBadge: { color: colors.accentGreen, fontWeight: 'bold', fontSize: 18 },
  debateBtn: { backgroundColor: colors.accentBlue, padding: 16, borderRadius: 12, alignItems: 'center' },
  debateBtnText: { color: 'white', fontWeight: 'bold' },
  zonePrice: { fontSize: 20, fontWeight: 'bold', color: colors.textPrimary, marginBottom: 8 },
  zoneDesc: { color: colors.textSecondary, fontSize: 14 }
});
