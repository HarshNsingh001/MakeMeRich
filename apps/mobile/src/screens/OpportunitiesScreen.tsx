import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { colors } from '../theme/colors';
import { fetchApi } from '../api/client';

export default function OpportunitiesScreen({ navigation }: any) {
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOpportunities();
  }, []);

  const loadOpportunities = async () => {
    setLoading(true);
    try {
      const data = await fetchApi('/stocks/opportunities');
      setOpportunities(data);
    } catch (e) {
      console.warn(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>AI Opportunities</Text>
      <Text style={styles.subHeader}>High conviction setups for today</Text>

      {loading ? (
        <ActivityIndicator size="large" color={colors.accentBlue} />
      ) : (
        <FlatList
          data={opportunities}
          keyExtractor={i => i.symbol}
          renderItem={({ item }) => (
            <TouchableOpacity 
              style={styles.card}
              onPress={() => navigation.navigate('StockDetail', { symbol: item.symbol })}
            >
              <View style={styles.rowBetween}>
                <Text style={styles.symbol}>{item.symbol}</Text>
                <Text style={styles.price}>₹{item.price}</Text>
              </View>
              <View style={styles.row}>
                <View style={[styles.badge, { 
                  backgroundColor: item.opportunity_level === 'HIGH' ? colors.accentGreen + '22' : colors.accentYellow + '22',
                  borderColor: item.opportunity_level === 'HIGH' ? colors.accentGreen : colors.accentYellow
                }]}>
                  <Text style={[styles.badgeText, { color: item.opportunity_level === 'HIGH' ? colors.accentGreen : colors.accentYellow }]}>
                    {item.opportunity_level}
                  </Text>
                </View>
                <Text style={styles.confText}>{(item.confidence * 100).toFixed(0)}% Confidence</Text>
              </View>
            </TouchableOpacity>
          )}
          ListEmptyComponent={<Text style={{ color: colors.textMuted }}>No opportunities found.</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary, padding: 20 },
  header: { fontSize: 24, fontWeight: 'bold', color: colors.textPrimary },
  subHeader: { fontSize: 14, color: colors.textSecondary, marginBottom: 20 },
  card: { backgroundColor: colors.bgCard, borderColor: colors.border, borderWidth: 1, borderRadius: 12, padding: 16, marginBottom: 12 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  symbol: { fontSize: 18, fontWeight: 'bold', color: colors.textPrimary },
  price: { fontSize: 18, fontWeight: 'bold', color: colors.textPrimary },
  row: { flexDirection: 'row', alignItems: 'center' },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, borderWidth: 1, marginRight: 12 },
  badgeText: { fontWeight: 'bold', fontSize: 10 },
  confText: { fontSize: 12, color: colors.textSecondary }
});
